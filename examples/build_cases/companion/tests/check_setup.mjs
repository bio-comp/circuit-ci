import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const html = fs.readFileSync(new URL("../firmware/setup.html", import.meta.url), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
async function session(mode, fail=false) {
  const fields = Object.fromEntries(["ssid","key","status","join","ethernet","forget"].map(k=>[k,{value:""}]));
  fields.ssid.value="Test-LAN"; fields.key.value="fixture12345";
  let receiver; const lines=[];
  const port={
    async open(){}, async close(){},
    readable:new ReadableStream({start(ctrl){receiver=ctrl;}}),
    writable:new WritableStream({write(bytes){
      const command=new TextDecoder().decode(bytes).trim(); lines.push(command);
      const reply=fail ? "ERR settings storage" : ({
        wifi:"SSID","Test-LAN":"KEY",fixture12345:"SAVED",forget:"FORGOTTEN",wired:"WIRED"
      })[command];
      receiver.enqueue(new TextEncoder().encode(reply+"\r\n"));
    }})
  };
  const ctx=vm.createContext({document:{getElementById:k=>fields[k],querySelectorAll:()=>[]},
    navigator:{serial:{requestPort:async()=>port}},TextEncoder,TextDecoder,
    setTimeout:(fn,ms)=>setTimeout(fn,ms===1100?0:ms),clearTimeout});
  vm.runInContext(script,ctx); await fields[mode].onclick();
  assert.equal(fields.key.value,"");
  return {lines,status:fields.status.textContent};
}
const joined=await session("join");
assert.deepEqual(joined.lines,["wifi","Test-LAN","fixture12345"]);
assert.match(joined.status,/saved/);
assert.match((await session("forget")).status,/removed/);
assert.match((await session("ethernet")).status,/selected/);
assert.match((await session("forget",true)).status,/rejected/);
console.log("USB provisioning, Ethernet selection, erase and rejected write passed (mock serial)");
