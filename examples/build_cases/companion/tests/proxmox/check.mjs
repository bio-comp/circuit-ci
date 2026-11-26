import assert from "node:assert/strict";
import {guestCard} from "./model.mjs";
const body = {data:[{type:"node",status:"online"}, {type:"qemu",vmid:101,status:"running"}, {type:"lxc",vmid:102,status:"stopped"}, {type:"qemu",vmid:103,status:"unknown"}]};
const sample={transport:"trusted",httpStatus:200,ageSeconds:10,body};
const expected={state:"visible guests",running:1,stopped:1,unknown:1};
const cases=[
  ["scoped live sample",{},expected],
  ["empty visible set",{body:{data:[]}},{state:"no visible guests"}],
  ["untrusted TLS",{transport:"invalid certificate"},{state:"transport unavailable"}],
  ["missing credential",{httpStatus:401},{state:"access unavailable"}],
  ["forbidden scope",{httpStatus:403},{state:"access unavailable"}],
  ["server failure",{httpStatus:503},{state:"service unavailable"}],
  ["stale buffer",{ageSeconds:61},{state:"stale"}],
  ["clock reversal",{ageSeconds:-1},{state:"stale"}],
  ["invalid body",{body:{data:null}},{state:"invalid response"}],
  ["duplicate guest",{body:{data:[body.data[1],body.data[1]]}},{state:"invalid response"}],
  ["incomplete rows",{body:{data:[{}]}},{state:"invalid response"}],
  ["age boundary",{ageSeconds:60},expected],
];
for(const [name,overrides,result] of cases){
  assert.deepEqual(guestCard({...sample,...overrides}),result,name);
  console.log(name, JSON.stringify(result));
}
