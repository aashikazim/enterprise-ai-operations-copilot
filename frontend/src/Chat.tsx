import {useEffect, useRef, useState, type FormEvent} from 'react'
import {useAuth} from './auth'
import type {AgentResult, Conversation, Message, Preview, RagResult, Source} from './contracts'

export default function Chat() {
  const {api} = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selected, setSelected] = useState<string | null>(null), [messages, setMessages] = useState<Message[]>([])
  const [mode, setMode] = useState('agent'), [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false), [loading, setLoading] = useState(false), [error, setError] = useState('')
  const [preview, setPreview] = useState<Preview | null>(null), [standalone, setStandalone] = useState<RagResult | null>(null)
  const waiting = useRef<AbortController | null>(null)
  const previewRequest = useRef<AbortController | null>(null)
  useEffect(() => { const controller = new AbortController(); api.request<{items:Conversation[]}>('/conversations', {signal:controller.signal}).then(v=>setConversations(v.items)).catch(e=>{if(e.name!=='AbortError')setError('Could not load conversations.')}); return ()=>controller.abort() }, [api])
  useEffect(() => {
    setMessages([]); setPreview(null); setError(''); previewRequest.current?.abort()
    if (!selected) return
    const controller = new AbortController(); setLoading(true)
    api.request<{messages:Message[]}>(`/conversations/${selected}`, {signal:controller.signal}).then(v=>setMessages(v.messages)).catch(e=>{if(e.name!=='AbortError')setError('Could not load this conversation.')}).finally(()=>{if(!controller.signal.aborted)setLoading(false)})
    return ()=>controller.abort()
  }, [api, selected])
  useEffect(()=>()=>{waiting.current?.abort();previewRequest.current?.abort()},[])
  async function create() {
    setError(''); setLoading(true)
    try {const value=await api.json<Conversation>('/conversations',{});setConversations(v=>[value,...v]);setSelected(value.id)}
    catch {setError('Could not create a conversation.')}
    finally {setLoading(false)}
  }
  async function inspect(source:Source) {
    setPreview(null);setError('')
    previewRequest.current?.abort(); const controller=new AbortController();previewRequest.current=controller
    try {const value=await api.request<Preview>(`/knowledge/documents/${source.document_id}/chunks/${source.chunk_index}`,{signal:controller.signal});if(!controller.signal.aborted)setPreview(value)}
    catch(e) {if(!(e instanceof Error&&e.name==='AbortError'))setError('This source is no longer available to your account.')}
  }
  function answer(value:RagResult, key:string) {
    return <article className="answer card" key={key}><p className="eyebrow">{value.abstained?'INSUFFICIENT EVIDENCE':'COPILOT'}</p><p className="answer-text">{value.answer.split(/(\[Source\s+\d+\])/i).map((part,i)=>{const match=part.match(/^\[Source\s+(\d+)\]$/i);const source=match&&value.sources.find(s=>s.source_id===Number(match[1]));return source?<button key={i} className="citation" onClick={()=>inspect(source)}>{part}</button>:<span key={i}>{part}</span>})}</p><small>{value.citation_validation.has_citations?'Source numbers checked; inspect the evidence for claim support.':'No citations in this answer.'}</small><div className="sources">{value.sources.map(s=><button key={s.source_id} className="secondary" onClick={()=>inspect(s)}>Source {s.source_id} · {s.title}</button>)}</div></article>
  }
  async function send(event:FormEvent) {
    event.preventDefault();if(!question.trim()||busy)return
    const text=question.trim();setBusy(true);setError('');setPreview(null)
    const controller=new AbortController();waiting.current=controller
    try {
      if(mode==='knowledge')setStandalone(await api.json<RagResult>('/rag/ask',{question:text},controller.signal))
      else if(selected){const result=await api.json<AgentResult>(`/conversations/${selected}/messages`,{question:text},controller.signal);setMessages(v=>[...v,{id:result.request_id+'u',role:'user',content:text},{id:result.request_id,role:'assistant',content:result.result.answer,result}])}
      setQuestion('')
    } catch(e) {setError(e instanceof Error&&e.name==='AbortError'?'Stopped waiting. The server may still finish; refresh the conversation before retrying.':'Request did not complete. Inspect the conversation before manually retrying.')} finally{setBusy(false);waiting.current=null}
  }
  async function resume() {
    if(!selected)return;setBusy(true);setError('')
    try{await api.json(`/conversations/${selected}/resume`,{});const value=await api.request<{messages:Message[]}>(`/conversations/${selected}`);setMessages(value.messages)}catch{setError('Resume unavailable. Check whether this conversation has an interrupted run.')}finally{setBusy(false)}
  }
  return <section className="page"><p className="eyebrow">KNOWLEDGE & OPERATIONS</p><h1>Ask. Inspect. Continue.</h1><div className="chat-layout"><section className="conversation-list card"><div className="row"><h2>Conversations</h2><button onClick={create} disabled={busy||loading}>New conversation</button></div>{!conversations.length&&<p>No conversations yet.</p>}{conversations.map(c=><button className={selected===c.id?'':'secondary'} key={c.id} disabled={busy} onClick={()=>setSelected(c.id)} aria-label={`Open conversation ${c.id}`}>Conversation {c.id.slice(0,8)}</button>)}</section><div className="stack"><div className="row"><label>Answer mode<select value={mode} disabled={busy} onChange={e=>setMode(e.target.value)}><option value="agent">Conversation agent</option><option value="knowledge">Knowledge question</option></select></label>{selected&&<button className="secondary" onClick={resume} disabled={busy}>Resume interrupted run</button>}</div>{loading&&<p role="status">Loading conversation…</p>}{mode==='agent'&&messages.map(m=>m.role==='user'?<div className="question card" key={m.id}><p className="eyebrow">YOU</p><p>{m.content}</p></div>:m.result?<div key={m.id}>{answer(m.result.result,m.id)}<details><summary>Execution steps</summary><ol>{(m.result.steps??[]).map((s,i)=><li key={i}>{s.node} · {s.status}</li>)}</ol>{(m.result.tool_results??[]).map((t,i)=><div key={i}><strong>{t.tool}</strong><pre>{JSON.stringify(t.items,null,2)}</pre></div>)}{(m.result.approvals??[]).map(a=><p key={a.id}>Proposed change {a.id.slice(0,8)} · {a.status}</p>)}</details></div>:<div className="card" key={m.id}>{m.content}</div>)}{mode==='knowledge'&&standalone&&answer(standalone,'direct')}{preview&&<section className="card" aria-label="Source preview"><h2>{preview.title}</h2><p className="answer-text">{preview.content}</p>{preview.truncated&&<small>Preview truncated.</small>}</section>}{error&&<p role="alert">{error}</p>}{busy&&<p role="status">Working on your question…</p>}<form onSubmit={send} className="card stack"><label>Your question<textarea rows={3} maxLength={2000} required value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask about your team’s knowledge or operations"/></label><div className="row"><button disabled={busy||loading||(mode==='agent'&&!selected)}>Send question</button>{busy&&waiting.current&&<button type="button" className="secondary" onClick={()=>waiting.current?.abort()}>Stop waiting</button>}<small>{mode==='agent'&&!selected?'Create or open a conversation to begin.':'Answers may be incomplete. Inspect sources before acting.'}</small></div></form></div></div></section>
}
