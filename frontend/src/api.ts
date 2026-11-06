export interface User { id: number; email: string; role: string; customer_id: number }
export class ApiError extends Error { constructor(public status: number) { super(status === 401 ? 'Session expired. Sign in again.' : 'Request failed. Please try again.') } }
export class ApiClient {
  private token: string | null = null
  onUnauthorized = () => {}
  setToken(token: string | null) { this.token = token }
  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers)
    if (this.token) headers.set('Authorization', `Bearer ${this.token}`)
    const response = await fetch('/api' + path, {...options, headers, credentials: 'omit'})
    if (!response.ok) {
      if (response.status === 401) { this.token = null; this.onUnauthorized() }
      throw new ApiError(response.status)
    }
    return response.status === 204 ? undefined as T : await response.json() as T
  }
  async login(email: string, password: string) {
    const value = await this.request<{access_token: string}>('/auth/login', {
      method: 'POST', body: new URLSearchParams({username: email, password}),
    })
    this.setToken(value.access_token)
    try { return await this.request<User>('/auth/me') }
    catch (error) { this.setToken(null); throw error }
  }
  json<T>(path: string, body: unknown) { return this.request<T>(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)}) }
}
