import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "../components/ui/AppLayout";
import { Badge, Button, Card } from "../components/ui";
import { paymentsApi } from "../api/client";
import { formatDate } from "../lib/format";
import { CustomerTimeline } from "../features/customers/CustomerTimeline";
import type { TimelineEvent } from "../features/customers/CustomerTimeline";
import type { ContractAppReportedStatus } from "../api/types";
import { ApiError, httpClient } from "../api/httpClient";

/** Forward moves a consuming app may report itself (design: contract-tracking). */
const NEXT_TRANSITION: Partial<Record<string, ContractAppReportedStatus>> = {
  generated: "sent",
  sent: "signed",
};

export function CustomerDetailPage() {
  const { customerId } = useParams<{ customerId: string }>();
  const queryClient = useQueryClient();
  const customerQuery = useQuery({
    queryKey: ["customer", customerId],
    queryFn: () => paymentsApi.customers.get(customerId!),
    enabled: Boolean(customerId),
  });

  const transition = useMutation({
    mutationFn: (status: ContractAppReportedStatus) =>
      paymentsApi.contracts.transition(customerQuery.data!.contract!.id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer", customerId] });
      queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
  });

  const sendForSignature = useMutation({
    mutationFn: () =>
      httpClient.post<{ signing_url: string }>(
        `/contracts/${customerQuery.data!.contract!.id}/send/`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer", customerId] });
    },
  });

  if (customerQuery.isLoading) {
    return <p className="state-message">Loading customer…</p>;
  }

  const customer = customerQuery.data;
  if (!customer) {
    return <p className="state-message error">Customer not found.</p>;
  }

  const contract = customer.contract;
  const nextStatus = contract ? NEXT_TRANSITION[contract.status] : undefined;

  const timeline: TimelineEvent[] = [];
  if (contract) {
    timeline.push({ id: `contract-created-${contract.id}`, date: contract.created_at, title: `Contract ${contract.status}`, kind: "contract" });
    if (contract.signed_at) {
      timeline.push({ id: `contract-signed-${contract.id}`, date: contract.signed_at, title: "Contract signed", kind: "contract" });
    }
  }
  if (customer.subscription) {
    if (customer.subscription.trial_start) {
      timeline.push({ id: `sub-trial-${customer.subscription.id}`, date: customer.subscription.trial_start, title: "Trial started", kind: "subscription" });
    }
    if (customer.subscription.trial_end) {
      timeline.push({ id: `sub-trial-end-${customer.subscription.id}`, date: customer.subscription.trial_end, title: "Trial ends", kind: "subscription" });
    }
  }
  timeline.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  return (
    <div>
      <PageHeader
        title={customer.display_name || customer.external_ref}
        description={`${customer.email || "no email"} · Customer since ${formatDate(customer.created_at)}`}
      />

      <div className="stat-row">
        <Card>
          <div className="stat-card-label">Contract</div>
          <div style={{ display: "flex", flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
            {contract ? <Badge tone={contract.status} /> : "—"}
            {contract && nextStatus && (
              <Button
                variant="secondary"
                disabled={transition.isPending}
                onClick={() => transition.mutate(nextStatus)}
              >
                {transition.isPending ? "Updating…" : `Mark ${nextStatus}`}
              </Button>
            )}
            {contract && contract.status === "generated" && (
              <Button
                disabled={sendForSignature.isPending}
                onClick={() => sendForSignature.mutate()}
              >
                {sendForSignature.isPending ? "Sending…" : "Send for signature"}
              </Button>
            )}
          </div>
          {sendForSignature.data?.signing_url && (
            <p style={{ marginTop: 8, fontSize: 13 }}>
              Signing link:{" "}
              <a href={sendForSignature.data.signing_url} target="_blank" rel="noreferrer">
                {sendForSignature.data.signing_url}
              </a>
            </p>
          )}
          {sendForSignature.isError && (
            <p className="state-message error" style={{ marginTop: 8 }}>
              {sendForSignature.error instanceof ApiError
                ? sendForSignature.error.message
                : "Sending for signature failed."}
            </p>
          )}
          {transition.isError && (
            <p className="state-message error" style={{ marginTop: 8 }}>
              {transition.error instanceof ApiError ? transition.error.message : "Transition failed."}
            </p>
          )}
        </Card>
        <Card>
          <div className="stat-card-label">Subscription</div>
          <div>{customer.subscription ? <Badge tone={customer.subscription.status} /> : "—"}</div>
        </Card>
        <Card>
          <div className="stat-card-label">Current period ends</div>
          <div>{customer.subscription?.current_period_end ? formatDate(customer.subscription.current_period_end) : "—"}</div>
        </Card>
      </div>

      <div className="section-title">Status Timeline</div>
      <CustomerTimeline events={timeline} />
    </div>
  );
}
