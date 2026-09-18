"""Contract template drafting via the Anthropic API.

Generation happens ONLY at template-authoring time (staff action in the
dashboard) — never per contract. Drafts always arrive with
`is_approved=False`; a human reviews the legal text before any customer
ever sees a document rendered from it.

The output contract text is drafted in professional Spanish (the
service's customers operate under Paraguayan law); the surrounding code
and placeholders stay in English.
"""

import os

from anthropic import Anthropic

from apps.contracts.models import DealType

# The closed set of placeholders the renderer substitutes — the model is
# instructed to use exactly these and no others.
AVAILABLE_PLACEHOLDERS = [
    "client_name",
    "client_email",
    "app_name",
    "plan_name",
    "monthly_fee_pyg",
    "trial_days",
    "trial_end",
    "contract_date",
]

_DEAL_TYPE_BRIEFS = {
    DealType.SAAS_SUBSCRIPTION: (
        "a Software-as-a-Service subscription agreement with a recurring "
        "monthly fee, a free trial period, service-availability terms, and "
        "suspension of access on non-payment"
    ),
    DealType.FIXED_WITH_OWNERSHIP: (
        "a fixed-price software development agreement where full code "
        "ownership and intellectual property transfer to the client upon "
        "final payment"
    ),
    DealType.FIXED_HOSTED: (
        "a fixed-price software development agreement where the provider "
        "retains code ownership and provides managed hosting; the client "
        "receives a usage license and hosting service terms"
    ),
}


def generate_template_body(*, deal_type: str, name: str, instructions: str = "") -> str:
    """Draft a contract template body (markdown) for `deal_type`."""
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
    brief = _DEAL_TYPE_BRIEFS.get(deal_type, _DEAL_TYPE_BRIEFS[DealType.SAAS_SUBSCRIPTION])

    system = (
        "You are drafting a reusable B2B contract template for a Paraguayan "
        "software services company. Write the contract in professional, "
        "neutral Spanish, governed by Paraguayan law, amounts in guaraníes. "
        "Output ONLY the contract document as markdown — no commentary. "
        "Use double-curly placeholders for variable data, choosing ONLY "
        "from this exact set: "
        + ", ".join("{{" + p + "}}" for p in AVAILABLE_PLACEHOLDERS)
        + ". The template will be reviewed by a human lawyer before use; "
        "include a final signature section for both parties."
    )
    user = f"Draft the template named '{name}' for {brief}."
    if instructions:
        user += f"\nAdditional instructions from the operator: {instructions}"

    # Streaming: contract documents are long; get_final_message avoids
    # HTTP timeouts without per-event handling.
    with client.messages.stream(
        model=model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        response = stream.get_final_message()

    return "".join(block.text for block in response.content if block.type == "text").strip()


def templatize_document(
    *, file_bytes: bytes, filename: str, deal_type: str, instructions: str = ""
) -> str:
    """Convert an uploaded contract (PDF or markdown/text) into a template.

    Claude rewrites the document as clean markdown and replaces the
    variable data (client names, fees, dates, ...) with the closed
    placeholder set, preserving the legal text otherwise.
    """
    import base64

    client = Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")

    system = (
        "You convert an existing contract document into a reusable template. "
        "Rewrite it as clean markdown, PRESERVING the legal text as written. "
        "Replace concrete variable data (client/party names, emails, fees, "
        "plan names, trial periods, dates) with double-curly placeholders "
        "chosen ONLY from this exact set: "
        + ", ".join("{{" + p + "}}" for p in AVAILABLE_PLACEHOLDERS)
        + ". Data that has no matching placeholder (company registration "
        "numbers, addresses) stays as [___] blanks. Output ONLY the "
        "markdown template — no commentary."
    )

    if filename.lower().endswith(".pdf"):
        content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.b64encode(file_bytes).decode(),
                },
            },
            {
                "type": "text",
                "text": f"Templatize this contract (deal type: {deal_type})."
                + (f"\nOperator instructions: {instructions}" if instructions else ""),
            },
        ]
    else:
        content = (
            f"Templatize this contract (deal type: {deal_type})."
            + (f"\nOperator instructions: {instructions}" if instructions else "")
            + "\n\n"
            + file_bytes.decode("utf-8", errors="replace")
        )

    with client.messages.stream(
        model=model,
        max_tokens=32000,
        system=system,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()

    return "".join(block.text for block in response.content if block.type == "text").strip()
