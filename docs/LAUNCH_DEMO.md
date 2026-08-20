# Short launch demo

This is a roughly 90-second presenter script. It uses only synthetic local data.

1. Say: “The agent says the refund completed. We are going to test the world it
   left behind, not grade that sentence.”
2. Run `agent-effects demo --agent naive --report`.
3. Point to `timeout_after_commit`: refund one durably committed, its
   acknowledgement was lost, and the retry used a new idempotency key.
4. Read the CLI result: “expected 1 refund; observed 2 refunds.”
5. Open the printed report. Show the two blue commit markers, the red injected
   fault, the two final refund records, and the stable contract codes.
6. Show that the reducer removed noise while retaining the same typed failure
   signature. Say “reduced counterexample,” not “globally minimal.”
7. Run `agent-effects demo --agent idempotent`; the same fault now passes because
   both attempts share a stable business idempotency key.

Close with: “No API key, model call, or hosted service. Agent Effects is an
experimental public alpha for deterministic pre-production testing of AI-agent
side effects.”
