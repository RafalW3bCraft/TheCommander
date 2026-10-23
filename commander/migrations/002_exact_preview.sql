-- Old pending proposals did not include the reconciliation marker in the hash.
-- Invalidate their authority and require a fresh proposal under the new contract.
UPDATE actions SET status='denied',error='Approval contract upgraded; create a new proposal'
WHERE NOT (arguments ? 'correlation_marker') AND status IN ('pending','approved');
UPDATE runs SET status='failed',error='Approval contract upgraded; create a new proposal'
WHERE status IN ('waiting_approval','queued') AND EXISTS
 (SELECT 1 FROM actions a WHERE a.run_id=runs.id AND a.error='Approval contract upgraded; create a new proposal');
UPDATE actions SET arguments=arguments || jsonb_build_object('correlation_marker','<!-- thecommander-action:' || id::text || ' -->')
WHERE NOT (arguments ? 'correlation_marker');
