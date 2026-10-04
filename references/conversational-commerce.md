# Conversational commerce — Meta Business Agent and the WhatsApp Business MCP

**Checked 2026-10-04.** Source grades, as in `references/content-credentials-by-platform.md`:

- **[P] Primary** — the vendor's own page, opened and read on 2026-10-04.
- **[S] Secondary** — press coverage (TechCrunch, here). Reported, not confirmed by us.
- **[G] SocialForge guidance** — editorial craft judgment. Not a platform fact, and no outcome claim is attached to it.

SocialForge produces the posts and copy that start conversations. It does **not** deploy, run or monitor a business agent, and it never sends a message to a customer. Nothing here changes that.

## What exists

### Meta Business Agent

- **[P]** Meta, "Be There for Every Customer With Meta Business Agent", 2026-06-03 — https://about.fb.com/news/2026/06/meta-business-agent/ . It can "Answer questions specific to your business", "Make product recommendations", "Book appointments and qualify incoming leads", and "Close sales"; businesses can "decide when a team member steps in to provide support"; the Meta Business Agent Platform "connects to a growing suite of hundreds of systems like Shopify, Zendesk, and Shopee." Meta's page describes it as live on WhatsApp and Messenger, with Instagram being added.
- **[S]** TechCrunch (Ivan Mehta), 2026-06-03 — https://techcrunch.com/2026/06/03/metas-ai-agent-for-whatsapp-business-is-now-available-globally/ . Reports availability "globally" after roughly two years of testing in India and Mexico, and lists WhatsApp Business, Instagram DMs and Messenger as surfaces. Meta's own page is more cautious about Instagram, so confirm which surfaces your account actually has.
- **Billing — read it live, never quote a figure.** Meta's pricing page ([P], https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages) says Business Agent messages are charged per token from 2026-08-01, and that service and utility messages start being charged from 2026-10-01. Rates change; send clients to that page instead of copying a number into a proposal.

### WhatsApp Business Tools MCP

- **[P]** Meta for Developers blog, 2026-09-15 — https://developers.facebook.com/blog/post/2026/09/15/whatsapp-business-messaging-mcp-ai-agent/ , and the setup guide https://developers.facebook.com/documentation/mcp/whatsapp-business-tools-mcp . Endpoint `https://mcp.facebook.com/whatsapp_business_tools`, Streamable HTTP, sign-in through a Meta developer account (OAuth), status "Beta - interface and tool set may change". Scopes requested: `business_management`, `whatsapp_business_management`, `whatsapp_business_messaging`.
- Tools, as listed by Meta (all prefixed `whatsapp_biz_`): `businesses`, `accounts`, `phone_numbers`, `add_phone_number`, `send_verification_code`, `verify_phone_number`, `register_phone_number`, `list_templates`, `get_template`, `create_template`, `update_template`, `delete_template`, `send_message`, `configure_webhooks`, `subscribe_webhook`, `configure_payments`, `verify_business`, `system_user_token`.
- Meta's own limit: "This release is built for development and testing workflows, not production sending at scale", and it "is rolling out gradually and may not be available to everyone yet."
- **[S]** TechCrunch (Sarah Perez), 2026-09-15 — https://techcrunch.com/2026/09/15/meta-now-lets-ai-agents-handle-the-boring-parts-of-whatsapp-business-setup/ . Reports the same setup tasks (creating the WhatsApp Business account, adding and verifying a phone number, registering for the Cloud API, creating and editing templates, testing messages and webhooks) and says it works with Claude, Cursor, Codex and ChatGPT.

**How SocialForge treats it.** The server is an optional, opt-in entry in `.mcp.json.connectors-reference` (`whatsapp-business-tools`) and is deliberately **not** in `.mcp.json.example`, because copying that file would connect everything in it. Use it for a one-off setup or template session with the user present — never inside the monthly pipeline. Of its tools, `send_message`, `configure_payments`, `verify_business` and `system_user_token` act on real customers, money or credentials: ask the user to approve each call by name before it runs, and confirm opt-in (below) before any send. Template drafting and listing are the safe, useful part.

## Rules that shape the copy

All **[P]** from Meta, read 2026-10-04.

- **Opt-in first.** "You can only send messages to WhatsApp users who have opted in to receiving messages from you." (https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages) The Business Messaging Policy (last updated 2026-09-23, https://whatsappbusiness.com/policy/) adds that you must "respect all requests (either on or off WhatsApp) by a person to block, discontinue, or otherwise opt out of communications from you."
- **The 24-hour window.** "When a WhatsApp user messages you or calls you, a 24-hour timer called a customer service window starts." Inside it you can reply without pre-approved templates; "To message WhatsApp users outside of a customer service window, use template messages instead." (same send-messages page)
- **Automation needs a way out.** "You may use automation when responding during the 24-hour window, but must also have available prompt, clear, and direct escalation paths." (policy page)
- **Disclosure that it is an AI.** Meta's announcement page, as read on 2026-10-04, makes no statement about telling customers they are talking to an AI. Whether your deployment must is a legal question (see `references/eu-ai-act-article50.md` for the EU transparency duties and take advice). SocialForge's stance is to say so in the first message.

## Playbooks — copy that works in conversational selling [G]

The post's job is to earn a first message. The conversation's job is to get one clear next step. Every playbook below is craft guidance; none of it is a measured result.

1. **The post asks for one tiny action.** A keyword the customer types, or a single question they can answer in a word — not a link and a paragraph of terms. The brand's `cta_keyword` is the front door when the brand runs a comment-keyword automation; `adapt-copy` already turns it into the CTA. One offer per post, and the post must not promise what the agent cannot answer (price, stock, delivery date).
2. **First reply: answer, then ask one thing.** Open with the answer to what they asked, in one to three short sentences. Then one question. Never a menu of six options.
3. **Recommend from the live catalog.** Product name, one reason in the customer's own words, current price and availability read from the catalog at the time of the message, one next step. Price and stock never live in stored copy.
4. **Qualify with a reason.** At most two or three questions before you offer something, and each says why it is asked ("so I don't send you the wrong size"). A questionnaire reads as a form, not a conversation.
5. **Close with a specific action.** "Want me to hold one for you?" beats "Let me know." One action per message; if the customer says no, offer the smaller step, not a repeat.
6. **Hand off on purpose.** Write the triggers down before launch: complaints and refunds, negotiation, anything the brand's compliance rules flag (health, legal, financial or comparative claims), and any second failed answer in a row. The handoff message says a person is joining and carries the context so the customer never repeats themselves. This is also what the policy's escalation path requires.
7. **Outside the window, use a template.** One purpose per template, written for someone who has not just messaged you, with the opt-out route visible. Meta approves templates and sets their category rules — read its current template guidelines before drafting, and treat approval as outside SocialForge's control.
8. **Say it is automated.** First message: who is replying and how to reach a person. Same honesty rule as the AI-assistance note on delivery manifests.
9. **Sourced or absent.** Every claim in a canned reply, template or agent instruction follows the same rule as post copy. Run them through the compliance check before they go to Meta or an agent:
   `python ${CLAUDE_PLUGIN_ROOT}/scripts/compliance_check.py --brand <brand> --text "<reply or template body>" --platform <platform>`

## What this file does not claim

- No conversion, revenue or response-time result for any agent. No source opened for this file reports one.
- No current price. See the billing note above.
- No coverage of other messaging platforms, or of Instagram or Messenger specifics beyond what the sources above state.

## Source ledger

| Claim area | URL | Grade | Checked |
|---|---|---|---|
| Business Agent capabilities | https://about.fb.com/news/2026/06/meta-business-agent/ | P | 2026-10-04 |
| Business Agent global availability | https://techcrunch.com/2026/06/03/metas-ai-agent-for-whatsapp-business-is-now-available-globally/ | S | 2026-10-04 |
| Business Agent and message billing | https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages | P | 2026-10-04 |
| WhatsApp Business Tools MCP (endpoint, scopes, tools) | https://developers.facebook.com/documentation/mcp/whatsapp-business-tools-mcp | P | 2026-10-04 |
| WhatsApp Business Tools MCP announcement | https://developers.facebook.com/blog/post/2026/09/15/whatsapp-business-messaging-mcp-ai-agent/ | P | 2026-10-04 |
| WhatsApp MCP coverage | https://techcrunch.com/2026/09/15/meta-now-lets-ai-agents-handle-the-boring-parts-of-whatsapp-business-setup/ | S | 2026-10-04 |
| Opt-in, 24-hour window, templates | https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages | P | 2026-10-04 |
| Opt-in, opt-out, automation escalation | https://whatsappbusiness.com/policy/ | P | 2026-10-04 |
