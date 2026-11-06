import {chromium, expect} from '@playwright/test'

const origin = process.env.E2E_ORIGIN
if (!origin || !/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)) throw new Error('Only owned loopback test origin permitted')
const browser = await chromium.launch({headless:true, ...(process.env.BROWSER_EXECUTABLE_PATH?{executablePath:process.env.BROWSER_EXECUTABLE_PATH}:{})})
try {
  const page = await browser.newPage({viewport:{width:1440,height:1000}})
  const errors = []
  page.on('pageerror', error=>errors.push(error.message))
  await page.goto(origin+'/chat')
  await expect(page.getByRole('heading',{name:'Sign in',exact:true})).toBeVisible()
  await page.getByLabel('Email',{exact:true}).fill('admin@acme.example')
  await page.getByLabel('Password',{exact:true}).fill('TestPassword123!')
  await page.getByRole('button',{name:'Continue to workspace'}).click()
  await expect(page.getByRole('heading',{name:'Clarity for the work ahead.'})).toBeVisible()
  await page.getByRole('link',{name:'Administration',exact:true}).click()
  await page.getByLabel('Document title',{exact:true}).fill('Synthetic MFA policy')
  await page.getByLabel('Document text',{exact:true}).fill('For MFA recovery contact the synthetic help desk.')
  const uploaded = page.waitForResponse(r=>r.url().endsWith('/api/knowledge/documents')&&r.request().method()==='POST')
  await page.getByRole('button',{name:'Add document',exact:true}).click()
  expect((await uploaded).status()).toBe(201)
  const foreignStatus = await page.evaluate(async id => {
    // Browser's application token is intentionally not exposed here: fetch cannot
    // access it. Probe through a temporary request interception instead below.
    return (await fetch(`/api/knowledge/documents/${id}/chunks/0`)).status
  },process.env.E2E_FOREIGN_DOCUMENT_ID)
  expect(foreignStatus).toBe(401)
  await page.getByRole('link',{name:'Conversations',exact:true}).click()
  await page.getByLabel('Answer mode').selectOption('knowledge')
  await page.getByLabel('Your question').fill('What is the MFA recovery policy?')
  await page.getByRole('button',{name:'Send question',exact:true}).click()
  await expect(page.getByText('Contact the synthetic help desk',{exact:false})).toBeVisible()
  // Swap only the preview target, leaving the real auth header untouched. The
  // server must reject another tenant's real document ID with 404.
  await page.route('**/api/knowledge/documents/*/chunks/*', async route=>{
    const target = new URL(route.request().url())
    target.pathname = `/api/knowledge/documents/${process.env.E2E_FOREIGN_DOCUMENT_ID}/chunks/0`
    await route.continue({url:target.toString()})
  })
  const denied = page.waitForResponse(r=>r.url().includes(`/knowledge/documents/${process.env.E2E_FOREIGN_DOCUMENT_ID}/chunks/0`))
  await page.getByRole('button',{name:'[Source 1]',exact:true}).click()
  expect((await denied).status()).toBe(404)
  await expect(page.getByRole('alert')).toContainText('no longer available')
  await page.unroute('**/api/knowledge/documents/*/chunks/*')
  await page.getByRole('button',{name:'[Source 1]',exact:true}).click()
  await expect(page.getByRole('region',{name:'Source preview'})).toContainText('For MFA recovery')
  await page.getByLabel('Answer mode').selectOption('agent')
  await page.getByRole('button',{name:'New conversation',exact:true}).click()
  await page.getByLabel('Your question').fill('list tickets')
  await page.getByRole('button',{name:'Send question',exact:true}).click()
  await page.getByText('Execution steps',{exact:true}).click()
  await expect(page.getByText('tickets.list',{exact:true})).toBeVisible()
  await page.getByLabel('Your question').fill(`close ticket ${process.env.E2E_TICKET_ID}`)
  await page.getByRole('button',{name:'Send question',exact:true}).click()
  await expect(page.getByText('Execution steps',{exact:true})).toHaveCount(2)
  await page.getByText('Execution steps',{exact:true}).last().click()
  await expect(page.getByText(/Proposed change/)).toBeVisible()
  await page.getByRole('link',{name:'Actions & history',exact:true}).click()
  await page.getByRole('button',{name:`Ticket ${process.env.E2E_TICKET_ID} · requested`,exact:true}).click()
  await expect(page.getByRole('button',{name:'Approve proposal'})).toBeDisabled()
  await page.getByLabel('I reviewed this specific ticket change.').check()
  await page.getByRole('button',{name:'Approve proposal',exact:true}).click()
  await expect(page.getByRole('button',{name:'Execute approved change'})).toBeDisabled()
  await page.getByLabel('I authorize applying this specific ticket change.').check()
  await page.getByRole('button',{name:'Execute approved change',exact:true}).click()
  await expect(page.locator('.badge').filter({hasText:'executed'})).toBeVisible()
  await page.getByRole('link',{name:'Administration',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Recorded quality signals'})).toBeVisible()
  await expect(page.getByRole('row',{name:'request count 1',exact:true})).toBeVisible()
  await expect(page.getByText('Pending evaluations',{exact:true})).toBeVisible()
  await page.setViewportSize({width:390,height:844})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.getByRole('button',{name:'Sign out',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Sign in',exact:true})).toBeVisible()
  expect(errors).toEqual([])
  console.log('Browser journey passed: login/upload/RAG/citations/tenant denial/conversation/tool/proposal/approve/execute/admin/mobile/logout; pageerrors=0')
} finally {
  await browser.close()
}
