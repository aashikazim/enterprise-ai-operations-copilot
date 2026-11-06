import {render, screen, fireEvent, waitFor} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {vi, test, expect, afterEach} from 'vitest'
import App from './App'
import {AuthProvider} from './auth'
import {ApiClient} from './api'
afterEach(() => vi.unstubAllGlobals())
function show() {render(<MemoryRouter initialEntries={['/']}><AuthProvider><App/></AuthProvider></MemoryRouter>)}
test('protected route requires login', () => {show(); expect(screen.getByRole('heading', {name:'Sign in'})).toBeInTheDocument(); expect(screen.getByLabelText('Email')).toBeRequired()})
test('login and logout keep token out of browser storage', async () => {
 const fetcher = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({access_token:'synthetic-token'}))).mockResolvedValueOnce(new Response(JSON.stringify({id:1,email:'user@example.com',role:'user',customer_id:1})))
 vi.stubGlobal('fetch',fetcher);show()
 fireEvent.change(screen.getByLabelText('Email'),{target:{value:'user@example.com'}});fireEvent.change(screen.getByLabelText('Password'),{target:{value:'SyntheticPassword!'}})
 fireEvent.click(screen.getByRole('button',{name:'Continue to workspace'}))
 await screen.findByRole('heading',{name:'Clarity for the work ahead.'})
 expect(localStorage.length).toBe(0);expect(sessionStorage.length).toBe(0)
 fireEvent.click(screen.getByRole('button',{name:'Sign out'}));await screen.findByRole('heading',{name:'Sign in'})
 expect(fetcher.mock.calls[1][1].headers.get('Authorization')).toBe('Bearer synthetic-token')
})
test('login failure is accessible and sanitized',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('PRIVATE',{status:401})));show();fireEvent.change(screen.getByLabelText('Email'),{target:{value:'user@example.com'}});fireEvent.change(screen.getByLabelText('Password'),{target:{value:'x'}});fireEvent.click(screen.getByRole('button',{name:'Continue to workspace'}));expect(await screen.findByRole('alert')).not.toHaveTextContent('PRIVATE')})
test('401 clears the client credential',async()=>{const fetcher=vi.fn().mockResolvedValueOnce(new Response('',{status:401})).mockResolvedValueOnce(new Response('{}'));vi.stubGlobal('fetch',fetcher);const api=new ApiClient();api.setToken('synthetic-token');const expired=vi.fn();api.onUnauthorized=expired;await expect(api.request('/private')).rejects.toThrow('Session expired');await api.request('/next');expect(expired).toHaveBeenCalledOnce();expect(fetcher.mock.calls[1][1].headers.has('Authorization')).toBe(false)})
