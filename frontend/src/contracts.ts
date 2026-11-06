export interface Source {source_id: number; document_id: number; title: string; chunk_index: number; similarity: number}
export interface RagResult {answer: string; sources: Source[]; abstained: boolean; citation_validation: {citations_valid: boolean; has_citations: boolean; invalid_source_ids: number[]; cited_source_ids: number[]}}
export interface AgentResult {request_id: string; mode: string; intent: string; result: RagResult; steps: {node: string; status: string}[]; tool_results: {tool: string; items: Record<string, unknown>[]}[]; approvals: {id: string; status: string}[]}
export interface Message {id: string; role: string; content: string; result?: AgentResult | null}
export interface Conversation {id: string; status: string; created_at: string; expires_at: string}
export interface Preview {title: string; content: string; truncated: boolean}
