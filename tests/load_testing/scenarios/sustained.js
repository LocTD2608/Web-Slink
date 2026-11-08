import http from 'k6/http';
import {sleep} from 'k6';
import {SharedArray} from 'k6/data';
import {Counter} from 'k6/metrics';
const users=new SharedArray('fixture',()=>JSON.parse(open('/results/fixture.json')).users);
const unexpected=new Counter('unexpected');
const full=new Counter('section_full');
const duplicate=new Counter('duplicate');
const rateLimited=new Counter('rate_limited');
const serverError=new Counter('server_error');
const target=Number(__ENV.VUS || 3000);
http.setResponseCallback(http.expectedStatuses(200,202,409));
export const options={
  stages:[{duration:__ENV.RAMP || '30s',target},{duration:__ENV.HOLD || '60s',target},{duration:'10s',target:0}],
  thresholds:{unexpected:['count==0']},
};
export default function(){
  unexpected.add(0); full.add(0); duplicate.add(0); rateLimited.add(0); serverError.add(0);
  const user=users[(__VU-1)%users.length];
  const headers={Authorization:'Bearer '+user.token,'Content-Type':'application/json','X-Idempotency-Key':'sustained-'+__VU};
  const catalog=http.get('http://nginx/api/v1/sections',{headers,tags:{name:'GET catalog'}});
  if(catalog.status!==200)unexpected.add(1);
  if(Math.random()<.2){
    const res=http.post('http://nginx/api/v1/registrations',JSON.stringify({section_id:'bench-section'}),{headers,tags:{name:'POST registration'}});
    if(res.status===409) {
      let code='';
      try {code=res.json().error_code;} catch { /* classified below */ }
      if(code==='SECTION_FULL') full.add(1);
      else if(code==='ALREADY_REGISTERED') duplicate.add(1);
      else unexpected.add(1);
    } else if(![200,202].includes(res.status)) {
      unexpected.add(1);
      if(res.status===429) rateLimited.add(1);
      if(res.status>=500) serverError.add(1);
    }
  }
  sleep(1+Math.random());
}
export function handleSummary(data){
  return {['/results/'+(__ENV.RUN_ID || 'sustained')+'-summary.json']:JSON.stringify(data,null,2)};
}
