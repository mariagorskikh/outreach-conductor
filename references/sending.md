# Sending: daily batches from the user's own mailbox

Only when `email.send_via` names a mail connector or tool that sends from the user's own
mailbox (for example a Gmail or Outlook connector). With `send_via: none`, the skill creates
drafts (or the hand-off file) and the report says nothing was sent.

In `autonomous` mode the agent sends after the self-review gate in `SKILL.md`, with no
approval step. In `review` mode it sends only a batch the user approved in chat.

## Every business day

1. Check for `SENDING_PAUSED` in the state folder. If it exists, do not send; report why.
2. Read new replies and bounces since the last batch (the mailbox, or the sends export). Put
   every opt-out ("stop", "unsubscribe", "not interested", "remove me") on the do-not-contact
   list (`icp.exclude_files`) before building the queue. Record bounces with `week.py sent`
   (`"bounced": true` on the row).
3. `week.py send-queue --out send-<date>.json --reviewed`. It takes `drafted` and `created`
   rows, highest fit first, removes opt-outs and excluded domains, skips rows a review held,
   skips unverified addresses unless `email.send_guesses` is true, adds `compliance.footer`,
   and stops at `email.daily_send_cap` minus what was already sent that day.
4. Send one at a time, spread through `email.business_hours` (for 50 over 8 hours, about one
   every 10 minutes, with some jitter). Send from the sender's own address, with the subject
   and body exactly as reviewed. If a draft already exists for the row (`draft_id`), send that
   draft rather than a copy, so there is never a second email.
5. After each send, confirm it left (it is in Sent, or the connector returned a message id).
   Append `{"key": ..., "sent_at": ..., "message_id": ...}` to `sent-<date>.jsonl` as you go.
6. At the end of the batch: `week.py sent sent-<date>.jsonl`, then `week.py crm --apply`.

## Stops during a batch

Stop the batch at once, keep what was recorded, and report:

- the mail provider shows a sending limit, a spam or policy warning, or asks to sign in again;
- `week.py sent` prints `SENDING PAUSED` (bounces above `email.bounce_stop`);
- a reply arrives from someone in the batch's company saying stop.

Do not retry around a stop. The next run checks the cause before sending again.

## New or quiet mailboxes

A mailbox or domain that has not sent cold email before needs warm-up: start near 10 a day
and raise slowly over two to three weeks. If the user says the mailbox is new, set
`email.daily_send_cap` low in the config at setup. Never buy a mailbox or a domain without
the user's yes (that is money).

## Follow-ups

This skill sends first touches. A second email to the same person is a separate decision the
config does not cover; leave it out unless the user adds a follow-up rule.
