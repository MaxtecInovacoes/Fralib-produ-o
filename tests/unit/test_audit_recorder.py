"""Audit system unit tests."""

import pytest
import os
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import FrozenInstanceError
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("SUPERADMIN_EMAIL", "su@x.com")

# Import after setting up mocks
from backend.audit.models import AuditEvent
from backend.audit.recorder import record_event, query_events, record_login, record_tenant_change, record_lead_change


@pytest.mark.unit
class TestAuditEvent:
    """Test AuditEvent dataclass."""

    def test_audit_event_creation(self):
        """Test creating an AuditEvent instance."""
        event = AuditEvent(
            tenant_id=1,
            actor_id=2,
            actor_email="test@example.com",
            actor_role="admin",
            action="user.update",
            entity_type="user",
            entity_id=3,
            diff={"name": "old", "name_new": "new"},
            ip="192.168.1.1",
            user_agent="Mozilla/5.0",
            metadata={"browser": "chrome"}
        )

        assert event.tenant_id == 1
        assert event.actor_id == 2
        assert event.actor_email == "test@example.com"
        assert event.actor_role == "admin"
        assert event.action == "user.update"
        assert event.entity_type == "user"
        assert event.entity_id == 3
        assert event.diff == {"name": "old", "name_new": "new"}
        assert event.ip == "192.168.1.1"
        assert event.user_agent == "Mozilla/5.0"
        assert event.metadata == {"browser": "chrome"}

    def test_audit_event_optional_fields(self):
        """Test AuditEvent with optional fields as None."""
        event = AuditEvent(
            tenant_id=None,
            actor_id=None,
            actor_email=None,
            actor_role="system",
            action="pipeline.publish",
            entity_type="pipeline",
            entity_id=1,
            diff={},
            ip=None,
            user_agent=None,
            metadata={}
        )

        assert event.tenant_id is None
        assert event.actor_id is None
        assert event.actor_email is None
        assert event.actor_role == "system"
        assert event.ip is None
        assert event.user_agent is None

    def test_audit_event_frozen(self):
        """Test that AuditEvent is immutable (frozen)."""
        event = AuditEvent(
            tenant_id=None,
            actor_id=None,
            actor_email=None,
            actor_role="user",
            action="login",
            entity_type="user",
            entity_id=None,
            diff={},
            ip=None,
            user_agent=None,
            metadata={},
        )

        with pytest.raises(FrozenInstanceError):
            event.actor_role = "admin"

    def test_audit_event_defaults(self):
        """Test AuditEvent with default values."""
        event = AuditEvent(
            tenant_id=None,
            actor_id=None,
            actor_email=None,
            actor_role="system",
            action="cron.cleanup",
            entity_type="system",
            entity_id=None,
            diff={},
            ip=None,
            user_agent=None,
            metadata={},
        )

        assert event.tenant_id is None
        assert event.actor_id is None
        assert event.actor_email is None
        assert event.ip is None
        assert event.user_agent is None

    def test_audit_event_serialization(self):
        """Test that AuditEvent can be serialized to dict."""
        event = AuditEvent(
            tenant_id=1,
            actor_id=2,
            actor_email="test@example.com",
            actor_role="admin",
            action="user.update",
            entity_type="user",
            entity_id=3,
            diff={"name": "old", "name_new": "new"},
            ip="192.168.1.1",
            user_agent="Mozilla/5.0",
            metadata={"browser": "chrome"}
        )

        event_dict = {
            "tenant_id": event.tenant_id,
            "actor_id": event.actor_id,
            "actor_email": event.actor_email,
            "actor_role": event.actor_role,
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "diff": event.diff,
            "ip": event.ip,
            "user_agent": event.user_agent,
            "metadata": event.metadata
        }

        assert event_dict == {
            "tenant_id": 1,
            "actor_id": 2,
            "actor_email": "test@example.com",
            "actor_role": "admin",
            "action": "user.update",
            "entity_type": "user",
            "entity_id": 3,
            "diff": {"name": "old", "name_new": "new"},
            "ip": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "metadata": {"browser": "chrome"}
        }


@pytest.mark.unit
class TestRecordEvent:
    """Test record_event function."""

    @patch('backend.audit.recorder.logger')
    def test_record_event_success(self, mock_logger):
        """Test successful event recording."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        event = AuditEvent(
            tenant_id=1,
            actor_id=2,
            actor_email="test@example.com",
            actor_role="admin",
            action="user.update",
            entity_type="user",
            entity_id=3,
            diff={"name": "old", "name_new": "new"},
            ip="192.168.1.1",
            user_agent="Mozilla/5.0",
            metadata={"browser": "chrome"}
        )

        record_event(mock_engine, event)

        # Verify connection was used
        mock_engine.connect.assert_called_once()

        # Verify INSERT was executed
        expected_diff_json = json.dumps({"name": "old", "name_new": "new"})
        expected_metadata_json = json.dumps({"browser": "chrome"})

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args
        sql = str(call_args[0][0])
        params = call_args[0][1]

        assert "INSERT INTO audit_events" in sql
        assert "tenant_id" in sql
        assert "actor_id" in sql
        assert "actor_email" in sql
        assert "actor_role" in sql
        assert "action" in sql
        assert "entity_type" in sql
        assert "entity_id" in sql
        assert "diff_json" in sql
        assert "ip" in sql
        assert "user_agent" in sql
        assert "metadata" in sql

        # Verify parameters
        assert params.get("tenant_id") == 1
        assert params.get("actor_id") == 2
        assert params.get("actor_email") == "test@example.com"
        assert params.get("actor_role") == "admin"
        assert params.get("action") == "user.update"
        assert params.get("entity_type") == "user"
        assert params.get("entity_id") == 3
        assert params.get("diff_json") == expected_diff_json
        assert params.get("ip") == "192.168.1.1"
        assert params.get("user_agent") == "Mozilla/5.0"
        assert params.get("metadata") == expected_metadata_json

        # Verify commit
        mock_connection.commit.assert_called_once()

        # No warning should be logged
        mock_logger.warning.assert_not_called()

    @patch('backend.audit.recorder.logger')
    def test_record_event_database_error(self, mock_logger):
        """Test recording event when database fails."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_connection.execute.side_effect = Exception("Database connection failed")

        event = AuditEvent(
            tenant_id=None,
            actor_id=None,
            actor_email=None,
            actor_role="system",
            action="cron.cleanup",
            entity_type="system",
            entity_id=None,
            diff={},
            ip=None,
            user_agent=None,
            metadata={},
        )

        # Should not raise exception
        record_event(mock_engine, event)

        # Warning should be logged
        mock_logger.warning.assert_called_once()

        # Commit should not be called
        mock_connection.commit.assert_not_called()

    @patch('backend.audit.recorder.logger')
    def test_record_event_complex_diff_json(self, mock_logger):
        """Test recording event with complex JSON diff."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        complex_diff = {
            "user": {"name": "John", "email": "john@example.com"},
            "settings": {"theme": "dark", "notifications": True},
            "array": [1, 2, 3],
            "nested": {"level1": {"level2": "value"}}
        }

        event = AuditEvent(
            tenant_id=1,
            actor_id=2,
            actor_email=None,
            actor_role="admin",
            action="user.update",
            entity_type="user",
            entity_id=3,
            diff=complex_diff,
            metadata={},
            ip="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        record_event(mock_engine, event)

        # Verify complex JSON was properly serialized (params is dict positional)
        call_args = mock_connection.execute.call_args
        params = call_args[0][1]
        expected_json = json.dumps(complex_diff)
        assert params.get("diff_json") == expected_json


@pytest.mark.unit
class TestQueryEvents:
    """Test query_events function."""

    @patch('backend.audit.recorder.logger')
    def test_query_events_no_filters(self, mock_logger):
        """Test querying events without filters."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        # Mock result rows
        row1 = MagicMock()
        row1._mapping = {"id": 1, "action": "login", "entity_type": "user"}
        row2 = MagicMock()
        row2._mapping = {"id": 2, "action": "logout", "entity_type": "user"}
        mock_connection.execute.return_value.fetchall.return_value = [row1, row2]

        events = query_events(mock_engine)

        assert len(events) == 2
        assert events[0]["id"] == 1
        assert events[0]["action"] == "login"
        assert events[1]["id"] == 2
        assert events[1]["action"] == "logout"

        # Verify basic SELECT query
        call_args = mock_connection.execute.call_args
        sql = str(call_args[0][0])
        assert "SELECT * FROM audit_events" in sql
        assert "ORDER BY criado_em DESC" in sql
        assert "LIMIT :limit" in sql
        assert call_args[0][1]["limit"] == 100

    @patch('backend.audit.recorder.logger')
    def test_query_events_with_filters(self, mock_logger):
        """Test querying events with filters."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        row1 = MagicMock()
        row1._mapping = {"id": 1, "action": "user.update", "entity_type": "user", "tenant_id": 1}
        mock_connection.execute.return_value.fetchall.return_value = [row1]

        events = query_events(
            mock_engine,
            tenant_id=1,
            actor_id=2,
            action="user.update",
            entity_type="user",
            since="2023-01-01",
            until="2023-12-31",
            limit=50,
        )

        assert len(events) == 1
        assert events[0]["id"] == 1

        # Verify query with WHERE clauses
        call_args = mock_connection.execute.call_args
        sql = str(call_args[0][0])
        params = call_args[0][1]
        assert "SELECT * FROM audit_events" in sql
        assert "WHERE tenant_id = :tenant_id" in sql
        assert "AND actor_id = :actor_id" in sql
        assert "AND action = :action" in sql
        assert "AND entity_type = :entity_type" in sql
        assert "AND criado_em >= :since" in sql
        assert "AND criado_em <= :until" in sql
        assert "ORDER BY criado_em DESC" in sql
        assert "LIMIT :limit" in sql
        assert params["limit"] == 50

        # Verify parameters
        assert params["tenant_id"] == 1
        assert params["actor_id"] == 2
        assert params["action"] == "user.update"
        assert params["entity_type"] == "user"
        assert params["since"] == "2023-01-01"
        assert params["until"] == "2023-12-31"

    @patch('backend.audit.recorder.logger')
    def test_query_events_partial_filters(self, mock_logger):
        """Test querying events with partial filters."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        row1 = MagicMock()
        row1._mapping = {"id": 1, "action": "login", "tenant_id": 1}
        mock_connection.execute.return_value.fetchall.return_value = [row1]

        events = query_events(mock_engine, tenant_id=1, action="login")

        assert len(events) == 1
        assert events[0]["id"] == 1

        # Verify query includes only provided filters
        call_args = mock_connection.execute.call_args
        sql = str(call_args[0][0])
        assert "WHERE tenant_id = :tenant_id" in sql
        assert "AND action = :action" in sql
        # Should not include filters that weren't provided
        assert "actor_id" not in sql or "WHERE actor_id" not in sql


@pytest.mark.unit
class TestRecordLogin:
    """Test record_login function."""

    @patch('backend.audit.recorder.logger')
    def test_record_login_success(self, mock_logger):
        """Test successful login recording."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        record_login(
            mock_engine,
            user_id=1,
            email="test@example.com",
            ip="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Verify INSERT was executed
        call_args = mock_connection.execute.call_args
        sql = str(call_args[0][0])
        params = call_args[0][1]

        assert "INSERT INTO audit_events" in sql
        assert params.get("action") == "auth.login"
        assert params.get("entity_type") == "user"
        assert params.get("actor_id") == 1
        assert params.get("actor_email") == "test@example.com"
        assert params.get("ip") == "192.168.1.1"
        assert params.get("user_agent") == "Mozilla/5.0"

        # Verify commit
        mock_connection.commit.assert_called_once()

    @patch('backend.audit.recorder.logger')
    def test_record_logout(self, mock_logger):
        """Test logout recording."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        record_login(
            mock_engine,
            user_id=1,
            email="test@example.com",
            ip="192.168.1.1",
            user_agent="Mozilla/5.0",
            action="auth.logout",
        )

        # Verify INSERT was executed for logout
        call_args = mock_connection.execute.call_args
        params = call_args[0][1]
        assert params.get("action") == "auth.logout"


@pytest.mark.unit
class TestRecordTenantChange:
    """Test record_tenant_change function."""

    @patch('backend.audit.recorder.logger')
    def test_record_tenant_change(self, mock_logger):
        """Test tenant change recording."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        before = {"theme": "light", "notifications": True}
        after = {"theme": "dark", "notifications": False}

        record_tenant_change(
            mock_engine,
            actor_id=1,
            tenant_id=2,
            before=before,
            after=after,
            ip="192.168.1.1",
        )

        # Verify INSERT was executed
        call_args = mock_connection.execute.call_args
        sql = str(call_args[0][0])
        params = call_args[0][1]

        assert "INSERT INTO audit_events" in sql
        assert params.get("action") == "tenant.update_settings"
        assert params.get("entity_type") == "tenant_settings"
        assert params.get("actor_id") == 1
        assert params.get("tenant_id") == 2
        assert params.get("diff_json") is not None
        parsed = json.loads(params["diff_json"])
        assert parsed == {"theme": ["light", "dark"], "notifications": [True, False]}
        assert params.get("ip") == "192.168.1.1"


@pytest.mark.unit
class TestRecordLeadChange:
    """Test record_lead_change function."""

    @patch('backend.audit.recorder.logger')
    def test_record_lead_create(self, mock_logger):
        """Test lead creation recording."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        diff = {"status": "new", "source": "manual"}

        record_lead_change(
            mock_engine,
            actor_id=1,
            tenant_id=2,
            lead_id=3,
            action="lead.create",
            diff=diff,
            ip="192.168.1.1",
        )

        # Verify INSERT was executed
        call_args = mock_connection.execute.call_args
        sql = str(call_args[0][0])
        params = call_args[0][1]

        assert "INSERT INTO audit_events" in sql
        assert params.get("action") == "lead.create"
        assert params.get("entity_type") == "lead"
        assert params.get("actor_id") == 1
        assert params.get("tenant_id") == 2
        assert params.get("entity_id") == 3
        assert params.get("diff_json") == json.dumps(diff)
        assert params.get("ip") == "192.168.1.1"

    @patch('backend.audit.recorder.logger')
    def test_record_lead_delete(self, mock_logger):
        """Test lead deletion recording."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        record_lead_change(
            mock_engine,
            actor_id=1,
            tenant_id=2,
            lead_id=3,
            action="lead.delete",
            diff={"deleted": True},
            ip="192.168.1.1",
        )

        # Verify INSERT was executed
        call_args = mock_connection.execute.call_args
        params = call_args[0][1]
        assert params.get("action") == "lead.delete"


@pytest.mark.unit
class TestAuditEndpoint:
    """Test the superadmin audit endpoint integration."""

    def test_audit_endpoint_accepts_superadmin_dict_user(self, monkeypatch):
        """current_user is a dict in most FraLib endpoints; it must use email."""
        from backend.core.auth import get_current_user
        from backend.endpoints import audit_endpoints as mod

        fake_engine = MagicMock()
        monkeypatch.setattr(mod, "engine", fake_engine)
        monkeypatch.setattr(
            mod,
            "query_events",
            lambda engine, **kwargs: [{"id": 1, "action": "auth.login"}],
        )

        app = FastAPI()
        app.include_router(mod.router)
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": 1,
            "email": "su@x.com",
            "role": "superadmin",
        }

        response = TestClient(app).get("/api/superadmin/audit")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["items"][0]["action"] == "auth.login"

    def test_audit_endpoint_rejects_non_superadmin_dict_user(self, monkeypatch):
        """A normal user dict must still receive 403."""
        from backend.core.auth import get_current_user
        from backend.endpoints import audit_endpoints as mod

        monkeypatch.setattr(mod, "query_events", MagicMock())

        app = FastAPI()
        app.include_router(mod.router)
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": 2,
            "email": "user@x.com",
            "role": "user",
        }

        response = TestClient(app).get("/api/superadmin/audit")

        assert response.status_code == 403
