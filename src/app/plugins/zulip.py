import json
import logging
from typing import Any
from uuid import UUID

import httpx

from app.domain.backlogs.models import Backlog
from app.domain.projects.models import Project
from app.lib.plugin import BacklogPlugin, ProjectPlugin
from app.lib.settings import server

__all__ = ["ZulipBacklogPlugin"]
logger = logging.getLogger(__name__)
backlog_topic: str = "📑 [BACKLOG] "


def log_info(message: str) -> None:
    return logger.info(message)


async def send_msg(backlog_data: "Backlog | dict[str, Any]") -> Any:
    log_info("sending message to zulip")
    url = f"{server.ZULIP_API_URL}{server.ZULIP_SEND_MESSAGE_URL}"
    auth = httpx.BasicAuth(server.ZULIP_EMAIL_ADDRESS, server.ZULIP_API_KEY)
    log_info(url)
    content: str
    stream_name: str
    if isinstance(backlog_data, Backlog):
        content = f"{backlog_data.status} {backlog_data.priority} {backlog_data.progress} **[{backlog_data.slug}]** {backlog_data.title}  **:time::{backlog_data.due_date.strftime('%d-%m-%Y')}** @**{backlog_data.assignee_name}** {backlog_data.category}"
        stream_name = f"📌PRJ/{backlog_data.project_name}"
    elif isinstance(backlog_data, dict):
        content = f"{backlog_data['status']} {backlog_data['priority']} {backlog_data['progress']} **[{backlog_data['slug']}]** {backlog_data['title']}  **:time::{backlog_data['due_date'].strftime('%d-%m-%Y')}** @**{backlog_data['assignee_name']}** {backlog_data['category']}"
        stream_name = f"📌PRJ/{backlog_data['project_name']}"
    log_info(content)
    data = {
        "type": "stream",
        "to": stream_name,
        "topic": backlog_topic,
        "content": content,
    }
    async with httpx.AsyncClient(timeout=1) as client:
        response = await client.post(url, auth=auth, data=data)
        if response.status_code == 200:
            return dict(response.json())
        raise httpx.HTTPError(f"{response.status_code}, {response.text}")


async def update_message(msg_id: int, content: str) -> dict[str, Any]:
    log_info("updaing message")
    url: str = f"{server.ZULIP_API_URL}{server.ZULIP_SEND_MESSAGE_URL}/{msg_id}"
    auth = httpx.BasicAuth(server.ZULIP_EMAIL_ADDRESS, server.ZULIP_API_KEY)

    data = {
        "topic": backlog_topic,
        "propagate_mode": "change_one",
        "send_notification_to_old_thread": "true",
        "send_notification_to_new_thread": "true",
        "content": content,
    }

    async with httpx.AsyncClient(timeout=1) as client:
        response = await client.patch(url, auth=auth, data=data)
        if response.status_code == 200:
            return dict(response.json())
        raise httpx.HTTPError(f"{response.status_code}, {response.text}")


class ZulipBacklogPlugin(BacklogPlugin):
    def __init__(self, zulip_bot: str = "pipo") -> None:
        self.zulip_bot: str = zulip_bot
        return

    async def before_create(self, data: "Backlog | dict[str, Any]") -> "Backlog | dict[str, Any]":
        log_info(self.zulip_bot)
        if isinstance(data, Backlog):
            data.plugin_meta = {"zulip_bot": self.zulip_bot}
        elif isinstance(data, dict):
            data["plugin_meta"] = {"zulip_bot": self.zulip_bot}
        return data

    async def after_create(self, data: "Backlog") -> "Backlog":
        log_info(self.zulip_bot)
        try:
            response = await send_msg(data)
            if response["result"] != "success":
                log_info(response)
            else:
                log_info("successfully sent message to zulip")
                data.plugin_meta = {"msg_id": response["id"]}

        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError, httpx.HTTPError) as e:
            log_info(f"failed to send message to zulip: {e!s}")
        return data

    async def before_update(self, item_id: str, data: "Backlog | dict[str, Any]") -> "Backlog | dict[str, Any]":
        return await super().before_update(item_id, data)

    async def after_update(self, data: "Backlog") -> "Backlog":
        log_info(self.zulip_bot)
        data = await super().after_update(data)
        content: str = f"{data.status} {data.priority} {data.progress} **[{data.slug}]** {data.title}  **:time::{data.due_date.strftime('%d-%m-%Y')}** @**{data.assignee_name}** {data.category}"
        try:
            msg_id = data.plugin_meta.get("msg_id")
            if msg_id:
                response: dict[str, Any] | None = await update_message(msg_id=msg_id, content=content)
            if response:
                if response.get("result") != "success":
                    log_info(str(response))
                else:
                    log_info(f"successfully sent message to zulip {response}")
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError, httpx.HTTPError) as e:
            log_info(f"failed to update message: {e!s}")
        return data

    async def before_delete(self, item_id: UUID) -> "UUID":
        log_info(self.zulip_bot)

        return item_id

    async def after_delete(self, data: "Backlog") -> "Backlog":
        log_info(self.zulip_bot)

        return data


async def create_stream(
    title: str,
    description: str,
    principals: list[str],
    is_pinned: bool | None = False,
) -> dict[str, str]:
    log_info("creating zulip stream")
    url: str = f"{server.ZULIP_API_URL}{server.ZULIP_CREATE_STREAM_URL}"
    auth = httpx.BasicAuth(server.ZULIP_EMAIL_ADDRESS, server.ZULIP_API_KEY)
    tag = f"📌PRJ/{title}" if is_pinned else f"PRJ/{title}"
    subscription: list[dict[str, str]] = [{"description": description, "name": tag}]
    data = {
        "subscriptions": json.dumps(subscription),
        "principals": json.dumps(principals),
        "invite_only": True,
        "history_public_to_subscribers": True,
    }
    async with httpx.AsyncClient(timeout=1) as client:
        response = await client.post(url, auth=auth, data=data)
        log_info(str(response))
        if response.status_code == 200:
            return dict(response.json())
        raise httpx.HTTPError(f"{response.status_code}, {response.text}")


class ZulipProjectPlugin(ProjectPlugin):
    def __init__(self, zulip_bot: str = "pipo") -> None:
        self.zulip_bot: str = zulip_bot
        return

    async def before_create(self, data: "Project | dict[str, Any]") -> "Project | dict[str, Any]":
        log_info(self.zulip_bot)
        if isinstance(data, Project):
            data.plugin_meta = {"zulip_bot": self.zulip_bot}
        elif isinstance(data, dict):
            data["plugin_meta"] = {"zulip_bot": self.zulip_bot}
            data["plugin_meta"] = {"zulip_object": self.zulip_bot}
        return data

    async def after_create(self, data: "Project") -> "Project":
        log_info(self.zulip_bot)
        try:
            principals: list[str] = server.ZULIP_ADMIN_EMAIL
            email: str
            email = "" if data.owner.email is None else data.owner.email
            principals.append(email)
            log_info(str(principals))
            response = await create_stream(data.name, data.description, principals, data.pin)
            if response["result"] != "success":
                log_info(str(response))
            else:
                log_info("successfully created zulip stream")
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError, httpx.HTTPError) as e:
            log_info(f"failed to create zulip stream: {e!s}")
        return data

    async def before_update(self, item_id: str, data: "Project | dict[str, Any]") -> "Project | dict[str, Any]":
        return await super().before_update(item_id, data)

    async def after_update(self, data: "Project") -> "Project":
        return await super().after_update(data)

    async def before_delete(self, item_id: UUID) -> "UUID":
        log_info(self.zulip_bot)

        return item_id

    async def after_delete(self, data: "Project") -> "Project":
        log_info(self.zulip_bot)

        return data
