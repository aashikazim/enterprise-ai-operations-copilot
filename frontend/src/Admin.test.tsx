import {render,screen,fireEvent,waitFor} from '@testing-library/react'
import {vi,test,expect,beforeEach} from 'vitest'
import Admin from './Admin'
const mocks=vi.hoisted(()=>({role:'admin',request:vi.fn(),json:vi.fn()}))
vi.mock('./auth',()=>({useAuth:()=>({user:{role:mocks.role},api:mocks})}))
const summary={jobs:{pending:2},expired_running_leases:1,oldest_pending_age_seconds:10,completed_in_window:4,average_processing_seconds:null,claim_verdicts:{supported:3},rag_metrics:{request_count:0,latency_p95_ms:null}}
beforeEach(()=>{mocks.role='admin';mocks.request.mockReset();mocks.json.mockReset();mocks.request.mockImplementation((path:string)=>Promise.resolve(path.includes('/summary')?summary:{items:[]}))})
test('regular user sees denied state and makes no admin requests',()=>{mocks.role='user';render(<Admin/>);expect(screen.getByRole('alert')).toHaveTextContent('cannot access');expect(mocks.request).not.toHaveBeenCalled()})
test('admin renders measured values and missing metrics honestly',async()=>{render(<Admin/>);await screen.findByText('Recorded quality signals');expect(screen.getByRole('heading',{name:'2'})).toBeInTheDocument();expect(screen.getAllByText('Not measured').length).toBeGreaterThan(0);expect(screen.getAllByText('No matching records.').length).toBe(2)})
test('record and status filters call scoped backend API',async()=>{render(<Admin/>);await screen.findByText('Recorded quality signals');fireEvent.change(screen.getByLabelText('Record type'),{target:{value:'tickets'}});fireEvent.change(screen.getByLabelText('Ticket status'),{target:{value:'closed'}});await waitFor(()=>expect(mocks.request.mock.calls.some(c=>c[0].includes('/admin/records/tickets?limit=20&offset=0&status=closed'))).toBe(true))})
test('backend errors are sanitized',async()=>{mocks.request.mockRejectedValue(new Error('PRIVATE SQL'));render(<Admin/>);expect(await screen.findByRole('alert')).not.toHaveTextContent('PRIVATE')})
