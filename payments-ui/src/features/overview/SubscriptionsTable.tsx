import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card, Table } from "../../components/ui";
import { formatDate } from "../../lib/format";
import { paymentsApi } from "../../api/client";
import type { Subscription } from "../../api/types";

export function SubscriptionsTable({ subscriptions }: { subscriptions: Subscription[] }) {
  const queryClient = useQueryClient();
  const initiate = useMutation({
    mutationFn: (subscriptionId: number) => paymentsApi.payments.initiate(subscriptionId),
    onSuccess: (payment) => {
      queryClient.invalidateQueries({ queryKey: ["payments"] });
      window.location.assign(`/payments/${payment.id}`);
    },
  });

  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <th>Subscription</th>
            <th>Customer ID</th>
            <th>Status</th>
            <th>Trial ends</th>
            <th>Current period ends</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {subscriptions.map((sub) => (
            <tr key={sub.id}>
              <td>#{sub.id}</td>
              <td>{sub.customer}</td>
              <td>
                <Badge tone={sub.status} />
              </td>
              <td>{sub.trial_end ? formatDate(sub.trial_end) : "—"}</td>
              <td>{sub.current_period_end ? formatDate(sub.current_period_end) : "—"}</td>
              <td>
                <Button
                  variant="secondary"
                  disabled={initiate.isPending}
                  onClick={() => initiate.mutate(sub.id)}
                >
                  {initiate.isPending && initiate.variables === sub.id ? "Starting…" : "Initiate payment"}
                </Button>
              </td>
            </tr>
          ))}
          {subscriptions.length === 0 && (
            <tr>
              <td colSpan={6} className="state-message">
                No subscriptions yet.
              </td>
            </tr>
          )}
        </tbody>
      </Table>
    </Card>
  );
}
