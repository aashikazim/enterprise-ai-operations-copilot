import {useState, type FormEvent} from 'react'
import {Navigate, NavLink, Outlet, Route, Routes} from 'react-router-dom'
import {useAuth} from './auth'
import Chat from './Chat'
import Admin from './Admin'

function Login() {
  const {user, login} = useAuth()
  const [email, setEmail] = useState(''), [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  if (user) return <Navigate to="/" replace/>
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try { await login(email, password); setPassword('') }
    catch { setError('Sign-in failed. Check your credentials or try again later.') }
    finally { setBusy(false) }
  }
  return <main className="login"><section className="login-intro"><p className="eyebrow">OPERATIONS / COPILOT</p><h1>Your knowledge.<br/>A clearer next step.</h1><p>Find grounded answers and review operations in your team’s workspace.</p></section><form onSubmit={submit} className="card login-form"><p className="eyebrow">WORKSPACE ACCESS</p><h2>Sign in</h2><label>Email<input type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)}/></label><label>Password<input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)}/></label>{error && <p role="alert">{error}</p>}<button disabled={busy}>{busy ? 'Signing in…' : 'Continue to workspace'}</button><small>Invitation-only access. Contact your team administrator for an account.</small></form></main>
}
function Shell() {
  const {user, logout} = useAuth()
  if (!user) return <Navigate to="/login" replace/>
  return <div className="workspace"><aside><a className="brand" href="#">OPS<span> / COPILOT</span></a><p className="eyebrow">YOUR WORKSPACE</p><nav aria-label="Workspace"><NavLink to="/" end>Overview</NavLink><NavLink to="/chat">Conversations</NavLink>{user.role==='admin'&&<NavLink to="/admin">Administration</NavLink>}</nav><div className="account"><small>{user.email}</small><button className="secondary" onClick={logout}>Sign out</button></div></aside><main id="main"><header><span>Enterprise operations</span><span className="badge">{user.role === 'admin' ? 'Administrator' : 'Team member'}</span></header><Outlet/></main></div>
}
function Overview() { return <section className="page"><p className="eyebrow">WORKSPACE</p><h1>Clarity for the work ahead.</h1><p className="lede">A shared place for trusted knowledge, accountable actions, and visible operations.</p><div className="grid"><article className="card"><span className="number">01</span><h2>Evidence first</h2><p>Answers stay connected to the sources your team can access.</p></article><article className="card"><span className="number">02</span><h2>Human decisions</h2><p>Proposed changes require an authorized person’s approval.</p></article><article className="card"><span className="number">03</span><h2>Operational visibility</h2><p>Review your team’s records and quality signals in one workspace.</p></article></div></section> }
export default function App() { return <><a className="skip" href="#main">Skip to main content</a><Routes><Route path="/login" element={<Login/>}/><Route element={<Shell/>}><Route index element={<Overview/>}/><Route path="/chat" element={<Chat/>}/><Route path="/admin" element={<Admin/>}/></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes></> }
