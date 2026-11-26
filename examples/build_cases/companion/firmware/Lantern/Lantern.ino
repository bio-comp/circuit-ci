#include <Arduino.h>
#include <Preferences.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <Wire.h>
#include "ethernet_report.h"

#ifndef FNK0104AB_2P8_240x320_ILI9341
#error Install the 2.8 inch Freenove FNK0104AB display profile before building
#endif

TFT_eSPI lcd;
TFT_eSprite frame(&lcd);
HardwareSerial modem(1);
Preferences prefs;
ModemReport pending, last;
constexpr int kRx = 14, kTx = 21;
constexpr uint16_t night=0x0884, mist=0xB617, turquoise=0x2E94, warm=0xFCE9, ink=0xFFFF;
uint32_t lastQuery=0, lastReply=0, lastDraw=0, sampleClock=0;
bool querying=false, haveReply=false, badReply=false, useWifi=false, touchPresent=false;
bool touchDown=false, keyDown=false;
int page=0;
char uartLine[88], usbLine[100], ssid[33];
size_t uartLen=0, usbLen=0;
bool uartOverflow=false, usbOverflow=false;
int setupStep=0;
uint32_t setupClock=0;
bool probeEnabled=false, pingQuery=false;
EchoResult echoResult;
uint32_t lastPingStart=0, lastPingDone=0, keyClock=0;
int pendingPing=-1;

uint32_t historyClock=0;
uint8_t history[24]{};
size_t historyPos=0, historySize=0;

void selectWifi(bool enabled) {
  useWifi=enabled; querying=false; badReply=false; haveReply=false;
  historyPos=0; historySize=0; last={}; pingQuery=false; echoResult.valid=false;
  if (!enabled) { WiFi.disconnect(true,false); return; }
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  String network=prefs.getString("ssid","");
  if (network.length()) WiFi.begin(network.c_str(),prefs.getString("key","").c_str());
}

void command(char* s) {
  if (setupStep && elapsed(millis(),setupClock,60000)) setupStep=0;
  if (setupStep==1) {
    if (!*s || strlen(s)>32) { setupStep=0; Serial.println("ERR SSID length"); return; }
    strlcpy(ssid,s,sizeof ssid); setupStep=2; setupClock=millis();
    Serial.println("KEY"); return;
  }
  if (setupStep==2) {
    setupStep=0;
    if (strlen(s)<8 || strlen(s)>63) { Serial.println("ERR WPA passphrase length"); return; }
    // Publish a new configuration only after both fields have been stored.
    if (!prefs.putBool("wifi",false)) { Serial.println("ERR settings storage"); return; }
    if (prefs.putString("key",s)!=strlen(s) || prefs.putString("ssid",ssid)!=strlen(ssid) ||
        !prefs.putBool("wifi",true)) {
      selectWifi(false); Serial.println("ERR settings storage"); return;
    }
    WiFi.disconnect(true,false); selectWifi(true); Serial.println("SAVED"); return;
  }
  if (!strcmp(s,"wifi")) { setupStep=1; setupClock=millis(); Serial.println("SSID"); }
  else if (!strcmp(s,"wired")) {
    if (!prefs.putBool("wifi",false)) { Serial.println("ERR settings storage"); return; }
    selectWifi(false); Serial.println("WIRED");
  }
  else if (!strcmp(s,"forget")) {
    if (!prefs.clear()) { Serial.println("ERR settings storage"); return; }
    probeEnabled=false; WiFi.disconnect(true,true); selectWifi(false);
    Serial.println("FORGOTTEN");
  } else if (!strcmp(s,"next")) page=(page+1)%3;
  else if (*s) Serial.println("Commands: wifi / wired / forget / next");
}

void serviceUsb() {
  if (setupStep && elapsed(millis(),setupClock,60000)) { setupStep=0; usbLen=0; }
  for (int count=0; count<140 && Serial.available();++count) {
    char c=Serial.read();
    if (c=='\r') continue;
    if (c=='\n') {
      usbLine[usbLen]=0;
      if (!usbOverflow) command(usbLine); else { setupStep=0; Serial.println("ERR input length"); }
      memset(usbLine,0,sizeof usbLine); usbLen=0; usbOverflow=false;
    } else if (c==0 || usbLen>=sizeof usbLine-1) usbOverflow=true;
    else usbLine[usbLen++]=c;
  }
}

void serviceModem(uint32_t now) {
  if (useWifi) return;
  if (querying && elapsed(now,lastQuery,pingQuery?4000:1500)) {
    querying=false;
    if (pingQuery) { echoResult.finish(-1); lastPingDone=now; }
    else badReply=true;
  }
  if (!querying && elapsed(now,lastQuery,2400)) {
    while (modem.available()) modem.read();
    pending={}; uartLen=0; uartOverflow=false;
    pingQuery=probeEnabled && haveReply && !badReply && !elapsed(now,lastReply,4000) &&
              last.addressed() && strcmp(last.gateway,"0.0.0.0") && elapsed(now,lastPingStart,15000);
    if (pingQuery) {
      echoResult.begin(last.gateway); pendingPing=-1;
      modem.printf("AT+PING=\"%s\"\r\n",echoResult.gateway); lastPingStart=now;
    } else modem.print("AT+CIPETH?\r\n");
    querying=true; lastQuery=now;
  }
  while (modem.available()) {
    char c=modem.read();
    if (!querying || c=='\r') continue;
    if (c=='\n') {
      uartLine[uartLen]=0;
      if (uartOverflow) pending.invalid=true;
      if (pingQuery) {
        if (!strcmp(uartLine,"OK") || !strcmp(uartLine,"ERROR")) {
          echoResult.finish((!strcmp(uartLine,"OK") && !pending.invalid) ? pendingPing : -1); lastPingDone=now; querying=false;
        } else if (!strncmp(uartLine,"+PING:",6)) {
          if (pending.seen) pending.invalid=true;
          pending.seen=1; pendingPing=pingMilliseconds(uartLine);
        }
      } else if (!strcmp(uartLine,"OK")) {
        querying=false; badReply=!pending.complete();
        if (!badReply) { last=pending; lastReply=now; haveReply=true; }
      } else if (!strcmp(uartLine,"ERROR")) { badReply=true; querying=false; }
      else pending.line(uartLine);
      uartLen=0; uartOverflow=false;
    } else if (c==0 || uartLen>=sizeof uartLine-1) uartOverflow=true;
    else uartLine[uartLen++]=c;
  }
}

bool touch() {
  if (!touchPresent) return false;
  Wire.beginTransmission(0x38); Wire.write(0x02);
  if (Wire.endTransmission(false)!=0 || Wire.requestFrom(uint8_t(0x38),size_t(1))!=1) return false;
  int contacts=Wire.read() & 0xf;
  return contacts==1 || contacts==2;
}

void displayText(const String& s,int x,int y,uint16_t color,int font=2) {
  frame.setTextColor(color,night); frame.drawString(s,x,y,font);
}

void render(uint32_t now) {
  bool wifiUp=useWifi && WiFi.status()==WL_CONNECTED && uint32_t(WiFi.localIP())!=0;
  bool expired=haveReply && elapsed(now,lastReply,6500);
  bool valid=!useWifi && haveReply && !expired && !badReply;
  bool addressed=wifiUp || (valid && last.addressed());
  String status;
  if (useWifi) status=wifiUp ? "Wi-Fi associated" : "Wi-Fi offline";
  else if (valid) status=addressed ? "Modem has an address" : "Awaiting address";
  else if (haveReply) status="Modem report stale";
  else status=badReply ? "No valid modem reply" : "Waiting for modem";

  if (elapsed(now, historyClock, 2500)) {
    history[historyPos] = addressed ? 2 : (valid ? 1 : 0);
    historyPos = (historyPos+1)%24;
    if (historySize<24) ++historySize;
    historyClock=now;
  }
  auto tint=addressed?turquoise:warm;
  frame.fillSprite(night);
  displayText("L A N   L A N T E R N",12,8,turquoise);
  displayText(useWifi?"WI-FI":"ETH / UART",209,8,mist);
  frame.drawFastHLine(12,33,296,mist);
  if (page==0) {
    displayText(status,12,45,ink,4);
    displayText("THIS INTERFACE",12,92,mist);
    String ip=wifiUp ? WiFi.localIP().toString() : (valid && last.addressed() ? String(last.ip) : String("--"));
    displayText(ip,12,114,tint,4);
    String info=wifiUp ? String("RSSI  ")+WiFi.RSSI()+" dBm" :
      (valid ? "UART query completed" : "USB setup: see gift card");
    displayText(info,12,166,mist);
  } else if (page==1) {
    displayText("Interface details",12,45,ink,4);
    displayText("Gateway",12,90,mist);
    displayText(wifiUp ? WiFi.gatewayIP().toString() : (valid?String(last.gateway):"--"),113,90,tint);
    displayText("Netmask",12,121,mist);
    displayText(wifiUp ? WiFi.subnetMask().toString() : (valid?String(last.mask):"--"),113,121,tint);
    displayText("Source",12,152,mist);
    displayText(useWifi?"Onboard station":"U138 address register",113,152,ink);
    String probe;
    if (useWifi || !probeEnabled) probe="Gateway probe off";
    else if (!valid || !echoResult.valid || elapsed(now,lastPingDone,23000) ||
             strcmp(echoResult.gateway,last.gateway)) probe="Gateway probe pending / stale";
    else if (echoResult.ms<0) probe="No confirmed echo reply";
    else probe="Gateway echo: "+String(echoResult.ms)+" ms";
    displayText(probe,12,179,mist);
  } else {
    displayText("Night watch",12,45,ink,4);
    for (int i=0;i<11;++i) frame.fillCircle(22+i*26,110+((i*39)%55),i%3==0?2:1,mist);
    int sparkle=22+int((now/70)%275);
    frame.drawFastHLine(12,170,290,tint);
    frame.fillCircle(sparkle,170,4,tint);
    frame.fillRoundRect(141,108,37,38,8,tint);
    frame.fillCircle(152,121,2,night); frame.fillCircle(167,121,2,night);
    frame.drawFastHLine(155,132,10,night);
    for (size_t i=0;i<historySize;++i) {
      uint8_t sample=history[(historyPos+24-historySize+i)%24];
      frame.fillRect(12+i*12,184,9,5,sample==2?turquoise:sample==1?warm:0xF209);
    }
    displayText("Address samples  /  last minute",12,190,mist);
  }
  frame.drawFastHLine(12,209,296,mist);
  displayText(String(page+1)+"/3    Tap or BOOT to turn page",12,215,mist);
  frame.pushSprite(0,0);
}

void setup() {
  Serial.begin(115200);
  prefs.begin("lantern",false);
  pinMode(0,INPUT_PULLUP);
  lcd.init(); lcd.setRotation(1); lcd.fillScreen(night);
  lcd.setTextColor(turquoise,night); lcd.drawString("LAN LANTERN",12,42,4);
  lcd.drawString("Starting the night watch",12,94,2);
  frame.setColorDepth(8);
  if (!frame.createSprite(320,240)) {
    lcd.drawString("Display buffer unavailable",12,130,2);
    while (true) delay(1000);
  }
  Wire.begin(16,15); Wire.setTimeOut(20);
  pinMode(18,OUTPUT); digitalWrite(18,LOW); delay(10); digitalWrite(18,HIGH); delay(150);
  Wire.beginTransmission(0x38); touchPresent=(Wire.endTransmission()==0);
  modem.begin(9600,SERIAL_8N1,kRx,kTx);
  probeEnabled=prefs.getBool("probe",false); selectWifi(prefs.getBool("wifi",false));
  Serial.println("READY");
}

void loop() {
  uint32_t now=millis();
  serviceUsb(); serviceModem(now);
  if (elapsed(now,sampleClock,60)) {
    bool t=touch(), k=digitalRead(0)==LOW;
    if (k&&!keyDown) keyClock=now;
    if (!k && keyDown && elapsed(now,keyClock,2000) && !useWifi) {
      probeEnabled=!probeEnabled; prefs.putBool("probe",probeEnabled); echoResult.valid=false; page=1;
      lastDraw=now-350;
    } else if ((t&&!touchDown)||(!k&&keyDown)) { page=(page+1)%3; lastDraw=now-350; }
    touchDown=t; keyDown=k; sampleClock=now;
  }
  if (elapsed(now,lastDraw,350)) { render(now); lastDraw=now; }
  delay(3);
}
