import pytest

from apps.contracts.models import (
    Contract,
    ContractStatus,
    ContractTemplate,
    InvalidContractTransition,
)


@pytest.fixture
def contract(db, app, customer_factory):
    template = ContractTemplate.objects.create(name="Standard", reference="tmpl-1")
    customer = customer_factory()
    return Contract.objects.create(customer=customer, template=template)


@pytest.mark.django_db
class TestContractLifecycle:
    def test_starts_in_draft(self, contract):
        assert contract.status == ContractStatus.DRAFT

    def test_valid_forward_transitions(self, contract):
        contract.transition_to(ContractStatus.GENERATED)
        assert contract.status == ContractStatus.GENERATED

        contract.transition_to(ContractStatus.SENT)
        assert contract.status == ContractStatus.SENT

        assert contract.signed_at is None
        contract.transition_to(ContractStatus.SIGNED)
        assert contract.status == ContractStatus.SIGNED
        assert contract.signed_at is not None

    def test_sent_can_be_declined(self, contract):
        contract.transition_to(ContractStatus.GENERATED)
        contract.transition_to(ContractStatus.SENT)
        contract.transition_to(ContractStatus.DECLINED)
        assert contract.status == ContractStatus.DECLINED

    def test_cannot_skip_states(self, contract):
        with pytest.raises(InvalidContractTransition):
            contract.transition_to(ContractStatus.SIGNED)

    def test_terminal_states_reject_further_transitions(self, contract):
        contract.transition_to(ContractStatus.VOIDED)
        with pytest.raises(InvalidContractTransition):
            contract.transition_to(ContractStatus.GENERATED)

    def test_signed_can_be_terminated(self, contract):
        contract.transition_to(ContractStatus.GENERATED)
        contract.transition_to(ContractStatus.SENT)
        contract.transition_to(ContractStatus.SIGNED)
        contract.transition_to(ContractStatus.TERMINATED)
        assert contract.status == ContractStatus.TERMINATED
