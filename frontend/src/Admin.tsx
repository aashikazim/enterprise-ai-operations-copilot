import {useEffect, useState, type FormEvent} from 'react'
import {useAuth} from './auth'

interface Summary {
 jobs:Record<string,number>;expired_running_leases:number;oldest_pending_age_seconds:number|null
 completed_in_window:number;average_processing_seconds:number|null
 claim_verdicts:Record<string,number>;rag_metrics:Record<string,number|null>
}
type Row=Record<string,unknown>
function display(value:unknown){return value===null||value===undefined?'Not measured':typeof value==='boolean'?(value?'Yes':'No'):String(value)}
function DataTable({rows,caption}:{rows:Row[];caption:string}) {
 const columns=rows.length?Object.keys(rows[0]):[]
 return <div className="scroll">{rows.length?<table><caption>{caption}</caption><thead><tr>{columns.map(c=><th key={c} scope="col">{c.replaceAll('_',' ')}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={String(r.id??i)}>{columns.map(c=><td key={c}>{display(r[c])}</td>)}</tr>)}</tbody></table>:<p>No matching records.</p>}</div>
}
export default function Admin() {
 const {api,user}=useAuth()
 const [summary,setSummary]=useState<Summary|null>(null),[records,setRecords]=useState<Row[]>([]),[jobs,setJobs]=useState<Row[]>([])
 const [kind,setKind]=useState('documents'),[offset,setOffset]=useState(0),[status,setStatus]=useState(''),[hours,setHours]=useState(24),[revision,setRevision]=useState(0)
 const [loading,setLoading]=useState(false),[error,setError]=useState(''),[title,setTitle]=useState(''),[content,setContent]=useState(''),[saving,setSaving]=useState(false),[notice,setNotice]=useState('')
 useEffect(()=>{
  if(user?.role!=='admin')return
  const controller=new AbortController();setLoading(true);setError('');setRecords([]);setSummary(null)
  Promise.all([
   api.request<Summary>(`/rag/monitoring/summary?hours=${hours}`,{signal:controller.signal}),
   api.request<{items:Row[]}>(`/admin/records/${kind}?limit=20&offset=${offset}${kind==='tickets'&&status?'&status='+status:''}`,{signal:controller.signal}),
   api.request<{items:Row[]}>('/rag/monitoring/jobs?status=failed&limit=20',{signal:controller.signal})
  ]).then(([s,r,j])=>{if(!controller.signal.aborted){setSummary(s);setRecords(r.items);setJobs(j.items)}})
   .catch(e=>{if(e.name!=='AbortError')setError('Could not load administration data.')})
   .finally(()=>{if(!controller.signal.aborted)setLoading(false)})
  return()=>controller.abort()
 },[api,user?.role,kind,offset,status,hours,revision])
 if(user?.role!=='admin')return <section className="page"><h1>Administrator access required</h1><p role="alert">Your account cannot access this view.</p></section>
 async function ingest(event:FormEvent){event.preventDefault();setSaving(true);setNotice('');setError('');try{await api.json('/knowledge/documents',{title,content});setTitle('');setContent('');setNotice('Document added.');setRevision(v=>v+1)}catch{setError('Document could not be added. Check content and service availability.')}finally{setSaving(false)}}
 return <section className="page stack">
  <div><p className="eyebrow">TENANT ADMINISTRATION</p><h1>A view of your operations.</h1><p className="lede">Records, evaluation signals, and work that needs attention.</p></div>
  <div className="row"><label>Reporting window<select value={hours} onChange={e=>setHours(Number(e.target.value))}><option value={24}>Last 24 hours</option><option value={168}>Last 7 days</option><option value={720}>Last 30 days</option></select></label><button className="secondary" onClick={()=>setRevision(v=>v+1)}>Refresh data</button></div>
  {loading&&<p role="status">Loading administration data…</p>}{error&&<p role="alert">{error}</p>}
  {summary&&<><div className="grid">
   <article className="card"><small>Pending evaluations</small><h2>{summary.jobs.pending??0}</h2><p>Oldest age: {display(summary.oldest_pending_age_seconds)} seconds</p></article>
   <article className="card"><small>Expired running leases</small><h2>{summary.expired_running_leases}</h2><p>Inspect stalled work before retrying.</p></article>
   <article className="card"><small>Completed in window</small><h2>{summary.completed_in_window}</h2><p>Average processing: {display(summary.average_processing_seconds)} seconds</p></article>
  </div><section className="card"><h2>Recorded quality signals</h2><p>Metrics reflect recorded samples. Missing measurements are shown explicitly.</p><table><caption>RAG request metrics</caption><thead><tr><th scope="col">Measure</th><th scope="col">Value</th></tr></thead><tbody>{Object.entries(summary.rag_metrics).map(([k,v])=><tr key={k}><th scope="row">{k.replaceAll('_',' ')}</th><td>{display(v)}</td></tr>)}</tbody></table><div className="row">{Object.entries(summary.claim_verdicts).map(([k,v])=><span className="badge" key={k}>{k}: {v}</span>)}</div></section></>}
  <section className="card stack"><div className="row"><h2>Enterprise records</h2><label>Record type<select value={kind} onChange={e=>{setKind(e.target.value);setOffset(0)}}><option value="documents">Documents</option><option value="tickets">Tickets</option><option value="users">Users</option></select></label>{kind==='tickets'&&<label>Ticket status<select value={status} onChange={e=>{setStatus(e.target.value);setOffset(0)}}><option value="">All statuses</option><option value="open">Open</option><option value="in_progress">In progress</option><option value="closed">Closed</option></select></label>}</div><DataTable rows={records} caption={'Authorized '+kind}/><div className="row"><button className="secondary" disabled={offset===0||loading} onClick={()=>setOffset(v=>Math.max(0,v-20))}>Previous records</button><span>Page {Math.floor(offset/20)+1}</span><button className="secondary" disabled={records.length<20||loading} onClick={()=>setOffset(v=>v+20)}>Next records</button></div></section>
  <section className="card"><h2>Failed evaluations</h2><DataTable rows={jobs} caption="Recent failed jobs"/></section>
  <form className="card stack" onSubmit={ingest}><h2>Add a knowledge document</h2><label>Document title<input required maxLength={255} value={title} onChange={e=>setTitle(e.target.value)}/></label><label>Document text<textarea required maxLength={20000} rows={5} value={content} onChange={e=>setContent(e.target.value)}/></label><button disabled={saving}>{saving?'Adding document…':'Add document'}</button>{notice&&<p role="status">{notice}</p>}</form>
 </section>
}
