import http from 'k6/http';
import {sleep} from 'k6';
import {SharedArray} from 'k6/data';
import {Counter} from 'k6/metrics';
const users=new SharedArray('fixture',()=>JSON.parse(open('/results/fixture.json')).users);
const unexpected=new Counter('unexpected');
const target=Number(__ENV.VUS || 3000);
http.setResponseCallback(http.expectedStatuses(200,202,409));
export const options={
  stages:[{duration:__ENV.RAMP || '30s',target},{duration:__ENV.HOLD || '60s',target},{duration:'10s',target:0}],
  thresholds:{unexpected:['count==0']},
};
export default function(){
  const user=users[(__VU-1)%users.length];
  const headers={Authorization:'Bearer '+user.token,'Content-Type':'application/json','X-Idempotency-Key':'sustained-'+__VU};
  const catalog=http.get('http://nginx/api/v1/sections',{headers,tags:{name:'GET catalog'}});
  if(catalog.status!==200)unexpected.add(1);
  if(Math.random()<.2){
    const res=http.post('http://nginx/api/v1/registrations',JSON.stringify({section_id:'bench-section'}),{headers,tags:{name:'POST registration'}});
    if(![200,202,409].includes(res.status))unexpected.add(1);
  }
  sleep(1+Math.random());
}
export function handleSummary(data){
  return {['/results/'+(__ENV.RUN_ID || 'sustained')+'-summary.json']:JSON.stringify(data,null,2)};
}
