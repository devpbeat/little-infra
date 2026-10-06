"""MerchantAccount credential storage and per-tenant resolution (Flow B).

Flow B charges a tenant's OWN buyer and the money must land in that
tenant's merchant account — never the SaaS owner's. These tests pin the
resolution order and the at-rest encryption of the private key.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.merchants.models import MerchantAccount
from payments_core.crypto import decrypt_secret, encrypt_secret
from payments_core.merchant_credentials import UnusableMerchantAccount, resolve_credentials


class TestSecretBox:
    def test_round_trips(self):
        assert decrypt_secret(encrypt_secret("priv-abc")) == "priv-abc"

    def test_ciphertext_is_not_plaintext(self):
        assert "priv-abc" not in encrypt_secret("priv-abc")

    def test_two_encryptions_differ(self):
        assert encrypt_secret("priv-abc") != encrypt_secret("priv-abc")

    def test_missing_key_fails_loudly(self, settings):
        settings.CREDENTIALS_ENCRYPTION_KEY = ""
        with pytest.raises(ImproperlyConfigured):
            encrypt_secret("priv-abc")


class TestMerchantAccountModel:
    def test_private_key_is_stored_encrypted(self, db, app):
        merchant = MerchantAccount.objects.create(
            app=app, external_ref="company-3", public_key="pub-3"
        )
        merchant.set_private_key("priv-3")
        merchant.save()
        merchant.refresh_from_db()

        assert merchant.get_private_key() == "priv-3"
        assert "priv-3" not in merchant.private_key_encrypted
        assert merchant.private_key_encrypted != ""

    def test_external_ref_unique_per_app(self, db, app):
        from django.db import IntegrityError

        MerchantAccount.objects.create(app=app, external_ref="company-3")
        with pytest.raises(IntegrityError):
            MerchantAccount.objects.create(app=app, external_ref="company-3")

    def test_same_external_ref_allowed_across_apps(self, db, app):
        from apps.apps_registry.models import ConsumingApp

        other = ConsumingApp.objects.create(name="other")
        MerchantAccount.objects.create(app=app, external_ref="company-3")
        MerchantAccount.objects.create(app=other, external_ref="company-3")

        assert MerchantAccount.objects.filter(external_ref="company-3").count() == 2


class TestCredentialResolution:
    def test_merchant_credentials_win(self, db, app, monkeypatch):
        monkeypatch.setenv("PAGOPAR_PUBLIC_KEY", "global-pub")
        monkeypatch.setenv("PAGOPAR_PRIVATE_KEY", "global-priv")
        merchant = MerchantAccount.objects.create(
            app=app, external_ref="company-3", public_key="pub-3", base_url="https://m3.test"
        )
        merchant.set_private_key("priv-3")
        merchant.save()

        creds = resolve_credentials(merchant=merchant)

        assert (creds.public_key, creds.private_key) == ("pub-3", "priv-3")
        assert creds.base_url == "https://m3.test"

    def test_falls_back_to_global_env_when_no_merchant(self, db, monkeypatch):
        """Flow A (SaaS subscriptions) keeps billing into the SaaS owner's account."""
        monkeypatch.setenv("PAGOPAR_PUBLIC_KEY", "global-pub")
        monkeypatch.setenv("PAGOPAR_PRIVATE_KEY", "global-priv")

        creds = resolve_credentials(merchant=None)

        assert (creds.public_key, creds.private_key) == ("global-pub", "global-priv")

    def test_merchant_without_keys_raises_instead_of_using_global(self, db, app, monkeypatch):
        """Never silently settle a tenant's money into the SaaS owner's account."""
        monkeypatch.setenv("PAGOPAR_PUBLIC_KEY", "global-pub")
        monkeypatch.setenv("PAGOPAR_PRIVATE_KEY", "global-priv")
        merchant = MerchantAccount.objects.create(app=app, external_ref="company-nokeys")

        with pytest.raises(UnusableMerchantAccount):
            resolve_credentials(merchant=merchant)
