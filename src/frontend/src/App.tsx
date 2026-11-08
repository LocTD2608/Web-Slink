import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { CourseCatalog } from './components/CourseCatalog';
import { TimetableMatrix } from './components/TimetableMatrix';
import { RegisteredList } from './components/RegisteredList';
import { CourseSectionDTO, StudentProfile, TicketStatusDTO } from './types/registration';
import { loginDemo, setToken, fetchSections, fetchStudentRegistrations, submitRegistration, dropRegistration, fetchRegistrationStatus } from './services/client';

export const App: React.FC = () => {
  const [studentId, setStudentId] = useState(localStorage.getItem('student') || 'std-0001');
  const [student, setStudent] = useState<StudentProfile>({id:studentId,student_code:'',full_name:'Sinh viên demo',major:'',max_credits:24,current_credits:0});
  const [sections, setSections] = useState<CourseSectionDTO[]>([]);
  const [enrolled, setEnrolled] = useState<CourseSectionDTO[]>([]);
  const [tab, setTab] = useState<'catalog'|'timetable'>('catalog');
  const [busy, setBusy] = useState(true);
  const [pending, setPending] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const scope = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const intent = useRef<{target:string; key:string}>();

  async function refresh(id = studentId, epoch = scope.current) {
    const [catalog, registrations] = await Promise.all([fetchSections(), fetchStudentRegistrations(id)]);
    if (epoch !== scope.current) return;
    setSections(catalog);
    setEnrolled(registrations);
    setStudent(s => ({...s, current_credits:registrations.reduce((n, r) => n+r.credits, 0)}));
  }

  async function inspect(ticket: string, epoch: number, attempt = 0) {
    if (epoch !== scope.current) return;
    try {
      const result = await fetchRegistrationStatus(ticket);
      if (epoch !== scope.current) return;
      if (['CONFIRMED','CANCELLED','FAILED'].includes(result.status)) {
        localStorage.removeItem('pending:'+studentId);
        setPending('');
        setBusy(false);
        intent.current = undefined;
        setMessage(result.status === 'FAILED' ? 'Yêu cầu thất bại: '+(result.reason || '') :
          result.status === 'CANCELLED' ? 'Đã xác nhận hủy học phần.' : 'Đăng ký thành công.');
        await refresh(studentId, epoch);
        return;
      }
    } catch {
      if (epoch !== scope.current) return;
      setMessage('Chưa kết nối được để xác nhận. Mã yêu cầu đã được giữ lại.');
    }
    if (attempt < 29) {
      timer.current = setTimeout(() => { void inspect(ticket, epoch, attempt+1); }, 1000);
    } else {
      setBusy(false);
      setMessage('Yêu cầu vẫn đang xử lý. Bạn có thể kiểm tra lại.');
    }
  }

  useEffect(() => {
    const epoch = ++scope.current;
    clearTimeout(timer.current);
    setBusy(true); setPending(''); setError(''); setMessage(''); setEnrolled([]);
    intent.current = undefined;
    localStorage.setItem('student', studentId);
    void loginDemo(studentId).then(async auth => {
      if (epoch !== scope.current) return;
      setToken(auth.token); setStudent(auth.student);
      await refresh(studentId, epoch);
      if (epoch !== scope.current) return;
      const ticket = localStorage.getItem('pending:'+studentId);
      if (ticket) { setPending(ticket); void inspect(ticket, epoch); }
      else setBusy(false);
    }).catch(err => {
      if (epoch === scope.current) { setError(err.message); setBusy(false); }
    });
    return () => { scope.current++; clearTimeout(timer.current); };
  }, [studentId]);

  async function act(section: CourseSectionDTO, drop = false) {
    const epoch = scope.current;
    if (busy || pending) return;
    if (drop && !window.confirm('Hủy đăng ký lớp '+section.section_code+'?')) return;
    const target = (drop ? 'drop:' : 'register:')+section.id;
    if (intent.current?.target !== target) intent.current = {target, key:crypto.randomUUID()};
    setBusy(true); setError(''); setMessage('');
    try {
      if (drop && !section.registration_id) throw new Error('Thiếu mã đăng ký. Hãy tải lại danh sách.');
      const result: TicketStatusDTO = drop
        ? await dropRegistration(section.registration_id!, intent.current.key)
        : await submitRegistration(section.id, intent.current.key);
      if (epoch !== scope.current) return;
      localStorage.setItem('pending:'+studentId, result.ticket_id);
      setPending(result.ticket_id);
      void inspect(result.ticket_id, epoch);
    } catch (err: unknown) {
      if (epoch !== scope.current) return;
      const failure = err as Error & {ticket_id?: string};
      if (failure.ticket_id) {
        localStorage.setItem('pending:'+studentId, failure.ticket_id);
        setPending(failure.ticket_id); void inspect(failure.ticket_id, epoch);
      } else { setError(failure.message); setBusy(false); }
    }
  }

  return <div className="min-h-screen bg-academic-canvas text-slate-800">
    <Header student={student} onRefresh={() => { void refresh().catch(e => setError(e.message)); }} isRefreshing={busy} />
    <main className="max-w-7xl mx-auto p-4 sm:p-6 space-y-5">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <label className="flex items-center gap-2">Sinh viên demo
          <select aria-label="Sinh viên demo" value={studentId} onChange={e => setStudentId(e.target.value)}
            className="border border-slate-300 rounded px-3 py-2 bg-white">
            {Array.from({length:10}, (_,i) => { const id='std-'+String(i+1).padStart(4,'0'); return <option key={id} value={id}>{id}</option>; })}
          </select>
        </label>
        <span className="text-slate-500">Môi trường thực hành • dữ liệu mẫu</span>
        <a className="underline text-blue-800" href="http://localhost:3001" target="_blank" rel="noreferrer">Grafana</a>
        <a className="underline text-blue-800" href="http://localhost:8001" target="_blank" rel="noreferrer">RedisInsight</a>
      </div>
      {error && <div role="alert" className="p-4 border border-red-300 bg-red-50 rounded text-red-800">{error}</div>}
      {pending && <div role="status" className="p-4 border border-amber-300 bg-amber-50 rounded space-y-2">
        <p className="font-semibold">Yêu cầu đang xử lý</p>
        <p className="text-sm break-all">Mã yêu cầu: {pending}</p>
        <button className="underline text-blue-900" onClick={() => {clearTimeout(timer.current); setBusy(true); void inspect(pending,scope.current);}}>Kiểm tra lại trạng thái</button>
      </div>}
      {message && <p role="status" className="text-sm">{message}</p>}
      <nav className="flex gap-3 border-b border-slate-300 pb-3" aria-label="Nội dung học phần">
        <button aria-pressed={tab==='catalog'} className={'px-4 py-2 rounded '+(tab==='catalog'?'bg-academic-primary text-white':'bg-white')} onClick={() => setTab('catalog')}>Danh mục lớp mở ({sections.length})</button>
        <button aria-pressed={tab==='timetable'} className={'px-4 py-2 rounded '+(tab==='timetable'?'bg-academic-primary text-white':'bg-white')} onClick={() => setTab('timetable')}>Thời khóa biểu</button>
      </nav>
      {tab==='catalog' ? <CourseCatalog sections={sections} enrolledSectionIds={new Set(enrolled.map(s=>s.id))}
        onRegister={s => {void act(s);}} isLoading={busy || !!pending} onRefresh={() => {void refresh().catch(e=>setError(e.message));}} isRefreshing={busy} />
        : <TimetableMatrix enrolledSections={enrolled} />}
      <RegisteredList enrolledSections={enrolled} onDrop={s=>{void act(s,true);}} isLoading={busy || !!pending}/>
      <p className="text-xs text-slate-500">Chạy kịch bản tải bằng scripts/lab.ps1. Chỉ xác nhận thành công sau khi dữ liệu được lưu vào PostgreSQL.</p>
    </main>
  </div>;
};

