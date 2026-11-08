import http from 'k6/http';
import { check, sleep } from 'k6';
import exec from 'k6/execution';
import { SharedArray } from 'k6/data';
import { Counter, Trend } from 'k6/metrics';
const users = new SharedArray('fixture', () => JSON.parse(open('/results/fixture.json')).users);
const generation = JSON.parse(open('/results/fixture.json')).generation;
const accepted = new Counter('accepted');
const confirmed = new Counter('confirmed');
const full = new Counter('section_full');
const unexpected = new Counter('unexpected');
const completion = new Trend('completion_duration', true);
const vus = Number(__ENV.VUS || 500);
const iterations = Number(__ENV.ITERATIONS || 6);
const expected = Math.min(60, vus*iterations);
const base = __ENV.BASE_URL || 'http://nginx';
http.setResponseCallback(http.expectedStatuses(200,202,409));
export const options = {
  scenarios: {flash:{executor:'per-vu-iterations',vus,iterations,maxDuration:'120s'}},
  thresholds: {
    accepted: ['count=='+expected],
    confirmed: ['count=='+expected],
    section_full: ['count=='+(vus*iterations-expected)],
    unexpected: ['count==0'],
    'http_req_duration{phase:register}': ['p(95)<30000'],
  },
  summaryTrendStats:['avg','min','med','max','p(95)','p(99)'],
};
export default function() {
  accepted.add(0); confirmed.add(0); full.add(0); unexpected.add(0);
  const index = exec.scenario.iterationInTest;
  const user = users[index];
  const headers = {'Content-Type':'application/json',Authorization:'Bearer '+user.token,
    'X-Idempotency-Key':generation+'-'+index};
  const start = Date.now();
  const res = http.post(base+'/api/v1/registrations',JSON.stringify({section_id:'bench-section'}),{headers,tags:{phase:'register',name:'POST registration'}});
  let body;
  try { body=res.json(); } catch { unexpected.add(1); return; }
  if (res.status===409 && body.error_code==='SECTION_FULL') { full.add(1); return; }
  if (res.status!==200 && res.status!==202) { unexpected.add(1); return; }
  accepted.add(1);
  for(let attempt=0; attempt<60 && ['PENDING','CANCEL_PENDING'].includes(body.status); attempt++) {
    sleep(1);
    const poll=http.get(base+'/api/v1/registrations/status/'+body.ticket_id,{headers,tags:{phase:'poll',name:'GET operation status'}});
    if (poll.status!==200) { unexpected.add(1); return; }
    body=poll.json();
  }
  const ok=body.status==='CONFIRMED';
  check(body,{'durably confirmed':()=>ok});
  if(ok) { confirmed.add(1); completion.add(Date.now()-start); }
  else unexpected.add(1);
}
export function handleSummary(data) {
  return {['/results/'+(__ENV.RUN_ID || 'flash')+'-summary.json']:JSON.stringify(data,null,2),
    stdout:JSON.stringify({requests:data.metrics.http_reqs.values.count,
      accepted:data.metrics.accepted.values.count,confirmed:data.metrics.confirmed.values.count,
      full:data.metrics.section_full.values.count,unexpected:data.metrics.unexpected.values.count})+'\n'};
}
