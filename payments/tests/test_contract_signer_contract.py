from adapters.fakes.fake_signer import NullContractSigner
from payments_core.ports.contract_signer import EnvelopeRequest, EnvelopeStatus


def test_create_envelope_returns_id():
    signer = NullContractSigner()
    result = signer.create_envelope(
        EnvelopeRequest(template_reference="tmpl-1", signer_name="Ada", signer_email="ada@example.com")
    )
    assert result.envelope_id


def test_envelope_status_is_signed():
    signer = NullContractSigner()
    result = signer.create_envelope(
        EnvelopeRequest(template_reference="tmpl-1", signer_name="Ada", signer_email="ada@example.com")
    )
    assert signer.get_envelope_status(result.envelope_id) == EnvelopeStatus.SIGNED
