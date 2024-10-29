import json
from pathlib import Path
from typing import Any

import pytest
from inline_snapshot import snapshot
from nonebug import App
from pytest_mock import MockerFixture
from respx import MockRouter

from tests.github.utils import MockBody, MockIssue, MockUser, get_github_bot


def check_json_data(file: Path, data: Any) -> None:
    with open(file, encoding="utf-8") as f:
        assert json.load(f) == data


@pytest.fixture
def mock_pull(mocker: MockerFixture):
    mock_pull = mocker.MagicMock()
    mock_pull.head.ref = "publish/issue1"
    mock_pull.draft = False

    return mock_pull


async def test_resolve_conflict_pull_requests_adapter(
    app: App, mocker: MockerFixture, mocked_api: MockRouter, tmp_path: Path, mock_pull
) -> None:
    from src.plugins.github import plugin_config
    from src.plugins.github.models import GithubHandler, RepoInfo
    from src.plugins.github.plugins.publish.utils import resolve_conflict_pull_requests

    mock_subprocess_run = mocker.patch("subprocess.run")
    mock_result = mocker.MagicMock()
    mock_subprocess_run.side_effect = lambda *args, **kwargs: mock_result

    mock_label = mocker.MagicMock()
    mock_label.name = "Adapter"

    mock_issue_repo = mocker.MagicMock()
    mock_issue = MockIssue(
        number=1,
        body=MockBody(type="adapter").generate(),
        user=MockUser(login="he0119", id=1),
    ).as_mock(mocker)
    mock_issue_repo.parsed_data = mock_issue

    mock_pull.labels = [mock_label]

    with open(tmp_path / "adapters.json", "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "module_name": "nonebot.adapters.onebot.v11",
                    "project_link": "nonebot-adapter-onebot",
                    "name": "OneBot V11",
                    "desc": "OneBot V11 协议",
                    "author_id": 1,
                    "homepage": "https://onebot.adapters.nonebot.dev/",
                    "tags": [],
                    "is_official": True,
                }
            ],
            f,
            ensure_ascii=False,
        )

    async with app.test_api() as ctx:
        adapter, bot = get_github_bot(ctx)

        handler = GithubHandler(bot=bot, repo_info=RepoInfo(owner="owner", repo="repo"))

        ctx.should_call_api(
            "rest.issues.async_get",
            snapshot({"owner": "owner", "repo": "repo", "issue_number": 1}),
            mock_issue_repo,
        )

        await resolve_conflict_pull_requests(handler, [mock_pull])
    # 测试 git 命令
    mock_subprocess_run.assert_has_calls(
        [
            mocker.call(["git", "fetch", "origin"], check=True, capture_output=True),
            mocker.call(
                ["git", "checkout", "publish/issue1"], check=True, capture_output=True
            ),
            mocker.call(["git", "checkout", "master"], check=True, capture_output=True),
            mocker.call(
                ["git", "switch", "-C", "publish/issue1"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                ["git", "config", "--global", "user.name", "he0119"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                [
                    "git",
                    "config",
                    "--global",
                    "user.email",
                    "he0119@users.noreply.github.com",
                ],
                check=True,
                capture_output=True,
            ),
            mocker.call(["git", "add", "-A"], check=True, capture_output=True),
            mocker.call(
                ["git", "commit", "-m", ":beers: publish adapter name (#1)"],
                check=True,
                capture_output=True,
            ),
            mocker.call(["git", "fetch", "origin"], check=True, capture_output=True),
            mocker.call(
                ["git", "diff", "origin/publish/issue1", "publish/issue1"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                ["git", "push", "origin", "publish/issue1", "-f"],
                check=True,
                capture_output=True,
            ),
        ]  # type: ignore
    )

    # 检查文件是否正确
    check_json_data(
        plugin_config.input_config.adapter_path,
        snapshot(
            [
                {
                    "module_name": "nonebot.adapters.onebot.v11",
                    "project_link": "nonebot-adapter-onebot",
                    "name": "OneBot V11",
                    "desc": "OneBot V11 协议",
                    "author_id": 1,
                    "homepage": "https://onebot.adapters.nonebot.dev/",
                    "tags": [],
                    "is_official": True,
                },
                {
                    "module_name": "module_name",
                    "project_link": "project_link",
                    "name": "name",
                    "desc": "desc",
                    "author_id": 1,
                    "homepage": "https://nonebot.dev",
                    "tags": [{"label": "test", "color": "#ffffff"}],
                    "is_official": False,
                },
            ]
        ),
    )

    assert mocked_api["homepage"].called


async def test_resolve_conflict_pull_requests_bot(
    app: App, mocker: MockerFixture, mocked_api: MockRouter, tmp_path: Path, mock_pull
) -> None:
    from src.plugins.github import plugin_config
    from src.plugins.github.models import GithubHandler, RepoInfo
    from src.plugins.github.plugins.publish.utils import resolve_conflict_pull_requests

    mock_subprocess_run = mocker.patch("subprocess.run")
    mock_result = mocker.MagicMock()
    mock_subprocess_run.side_effect = lambda *args, **kwargs: mock_result

    mock_issue_repo = mocker.MagicMock()
    mock_issue = MockIssue(
        number=1,
        body=MockBody(type="bot").generate(),
        user=MockUser(login="he0119", id=1),
    ).as_mock(mocker)
    mock_issue_repo.parsed_data = mock_issue

    mock_label = mocker.MagicMock()
    mock_label.name = "Bot"

    mock_pull.labels = [mock_label]

    with open(tmp_path / "bots.json", "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "name": "CoolQBot",
                    "desc": "基于 NoneBot2 的聊天机器人",
                    "author_id": 1,
                    "homepage": "https://github.com/he0119/CoolQBot",
                    "tags": [],
                    "is_official": False,
                }
            ],
            f,
            ensure_ascii=False,
        )

    async with app.test_api() as ctx:
        adapter, bot = get_github_bot(ctx)

        handler = GithubHandler(bot=bot, repo_info=RepoInfo(owner="owner", repo="repo"))

        ctx.should_call_api(
            "rest.issues.async_get",
            snapshot({"owner": "owner", "repo": "repo", "issue_number": 1}),
            mock_issue_repo,
        )

        await resolve_conflict_pull_requests(handler, [mock_pull])

    # 测试 git 命令
    mock_subprocess_run.assert_has_calls(
        [
            mocker.call(["git", "fetch", "origin"], check=True, capture_output=True),
            mocker.call(
                ["git", "checkout", "publish/issue1"], check=True, capture_output=True
            ),
            mocker.call(["git", "checkout", "master"], check=True, capture_output=True),
            mocker.call(
                ["git", "switch", "-C", "publish/issue1"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                ["git", "config", "--global", "user.name", "he0119"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                [
                    "git",
                    "config",
                    "--global",
                    "user.email",
                    "he0119@users.noreply.github.com",
                ],
                check=True,
                capture_output=True,
            ),
            mocker.call(["git", "add", "-A"], check=True, capture_output=True),
            mocker.call(
                ["git", "commit", "-m", ":beers: publish bot name (#1)"],
                check=True,
                capture_output=True,
            ),
            mocker.call(["git", "fetch", "origin"], check=True, capture_output=True),
            mocker.call(
                ["git", "diff", "origin/publish/issue1", "publish/issue1"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                ["git", "push", "origin", "publish/issue1", "-f"],
                check=True,
                capture_output=True,
            ),
        ]  # type: ignore
    )

    # 检查文件是否正确
    check_json_data(
        plugin_config.input_config.bot_path,
        snapshot(
            [
                {
                    "name": "CoolQBot",
                    "desc": "基于 NoneBot2 的聊天机器人",
                    "author_id": 1,
                    "homepage": "https://github.com/he0119/CoolQBot",
                    "tags": [],
                    "is_official": False,
                },
                {
                    "name": "name",
                    "desc": "desc",
                    "author_id": 1,
                    "homepage": "https://nonebot.dev",
                    "tags": [{"label": "test", "color": "#ffffff"}],
                    "is_official": False,
                },
            ]
        ),
    )

    assert mocked_api["homepage"].called


async def test_resolve_conflict_pull_requests_plugin(
    app: App, mocker: MockerFixture, mocked_api: MockRouter, tmp_path: Path, mock_pull
) -> None:
    from src.plugins.github import plugin_config
    from src.plugins.github.models import GithubHandler, RepoInfo
    from src.plugins.github.plugins.publish.utils import resolve_conflict_pull_requests
    from src.providers.docker_test import Metadata

    mock_subprocess_run = mocker.patch("subprocess.run")
    mock_result = mocker.MagicMock()
    mock_subprocess_run.side_effect = lambda *args, **kwargs: mock_result

    mock_label = mocker.MagicMock()
    mock_label.name = "Plugin"

    mock_issue_repo = mocker.MagicMock()
    mock_issue = MockIssue(
        number=1,
        body=MockBody(type="plugin").generate(),
        user=MockUser(login="he0119", id=1),
    ).as_mock(mocker)
    mock_issue_repo.parsed_data = mock_issue

    mock_pull.labels = [mock_label]
    mock_pull.title = "Plugin: 帮助"

    mock_comment = mocker.MagicMock()
    mock_comment.body = "Plugin: test"
    mock_list_comments_resp = mocker.MagicMock()
    mock_list_comments_resp.parsed_data = [mock_comment]

    mock_test_result = mocker.MagicMock()
    mock_test_result.metadata = Metadata(
        name="name",
        desc="desc",
        homepage="https://nonebot.dev",
        type="application",
        supported_adapters=["~onebot.v11"],
    )
    mock_docker = mocker.patch("src.providers.docker_test.DockerPluginTest.run")
    mock_docker.return_value = mock_test_result

    with open(tmp_path / "plugins.json", "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "module_name": "nonebot_plugin_treehelp",
                    "project_link": "nonebot-plugin-treehelp",
                    "author_id": 1,
                    "tags": [],
                    "is_official": True,
                }
            ],
            f,
            ensure_ascii=False,
        )

    async with app.test_api() as ctx:
        adapter, bot = get_github_bot(ctx)

        handler = GithubHandler(bot=bot, repo_info=RepoInfo(owner="owner", repo="repo"))

        ctx.should_call_api(
            "rest.issues.async_get",
            snapshot({"owner": "owner", "repo": "repo", "issue_number": 1}),
            mock_issue_repo,
        )
        ctx.should_call_api(
            "rest.issues.async_list_comments",
            {"owner": "owner", "repo": "repo", "issue_number": 1},
            mock_list_comments_resp,
        )

        await resolve_conflict_pull_requests(handler, [mock_pull])

    # 测试 git 命令
    mock_subprocess_run.assert_has_calls(
        [
            mocker.call(["git", "fetch", "origin"], check=True, capture_output=True),
            mocker.call(
                ["git", "checkout", "publish/issue1"], check=True, capture_output=True
            ),
            mocker.call(["git", "checkout", "master"], check=True, capture_output=True),
            mocker.call(
                ["git", "switch", "-C", "publish/issue1"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                ["git", "config", "--global", "user.name", "he0119"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                [
                    "git",
                    "config",
                    "--global",
                    "user.email",
                    "he0119@users.noreply.github.com",
                ],
                check=True,
                capture_output=True,
            ),
            mocker.call(["git", "add", "-A"], check=True, capture_output=True),
            mocker.call(
                ["git", "commit", "-m", ":beers: publish plugin name (#1)"],
                check=True,
                capture_output=True,
            ),
            mocker.call(["git", "fetch", "origin"], check=True, capture_output=True),
            mocker.call(
                ["git", "diff", "origin/publish/issue1", "publish/issue1"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                ["git", "push", "origin", "publish/issue1", "-f"],
                check=True,
                capture_output=True,
            ),
        ]  # type: ignore
    )

    # 检查文件是否正确
    # 因为没有进行 git 操作，所有会有两个插件信息
    check_json_data(
        plugin_config.input_config.plugin_path,
        snapshot(
            [
                {
                    "module_name": "nonebot_plugin_treehelp",
                    "project_link": "nonebot-plugin-treehelp",
                    "author_id": 1,
                    "tags": [],
                    "is_official": True,
                },
                {
                    "module_name": "module_name",
                    "project_link": "project_link",
                    "author_id": 1,
                    "tags": [{"label": "test", "color": "#ffffff"}],
                    "is_official": False,
                },
            ]
        ),
    )

    assert mocked_api["homepage"].called


async def test_resolve_conflict_pull_requests_draft(
    app: App, mocker: MockerFixture, mocked_api: MockRouter, tmp_path: Path
) -> None:
    from src.plugins.github import plugin_config
    from src.plugins.github.models import GithubHandler, RepoInfo
    from src.plugins.github.plugins.publish.utils import resolve_conflict_pull_requests

    mock_subprocess_run = mocker.patch("subprocess.run")
    mock_result = mocker.MagicMock()
    mock_subprocess_run.side_effect = lambda *args, **kwargs: mock_result

    mock_label = mocker.MagicMock()
    mock_label.name = "Bot"

    mock_pull = mocker.MagicMock()
    mock_pull.head.ref = "publish/issue1"
    mock_pull.draft = True
    mock_pull.labels = [mock_label]

    with open(tmp_path / "bots.json", "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "name": "CoolQBot",
                    "desc": "基于 NoneBot2 的聊天机器人",
                    "author_id": 1,
                    "homepage": "https://github.com/he0119/CoolQBot",
                    "tags": [],
                    "is_official": False,
                }
            ],
            f,
            ensure_ascii=False,
        )

    async with app.test_api() as ctx:
        adapter, bot = get_github_bot(ctx)

        handler = GithubHandler(bot=bot, repo_info=RepoInfo(owner="owner", repo="repo"))

        await resolve_conflict_pull_requests(handler, [mock_pull])

    # 测试 git 命令
    mock_subprocess_run.assert_not_called()

    # 检查文件是否正确
    check_json_data(
        plugin_config.input_config.bot_path,
        [
            {
                "name": "CoolQBot",
                "desc": "基于 NoneBot2 的聊天机器人",
                "author_id": 1,
                "homepage": "https://github.com/he0119/CoolQBot",
                "tags": [],
                "is_official": False,
            }
        ],
    )

    assert not mocked_api["homepage"].called


async def test_resolve_conflict_pull_requests_ref(
    app: App, mocker: MockerFixture, mocked_api: MockRouter, tmp_path: Path
) -> None:
    from src.plugins.github import plugin_config
    from src.plugins.github.models import GithubHandler, RepoInfo
    from src.plugins.github.plugins.publish.utils import resolve_conflict_pull_requests

    mock_subprocess_run = mocker.patch("subprocess.run")
    mock_result = mocker.MagicMock()
    mock_subprocess_run.side_effect = lambda *args, **kwargs: mock_result

    mock_label = mocker.MagicMock()
    mock_label.name = "Bot"

    mock_pull = mocker.MagicMock()
    mock_pull.head.ref = "publish/issue"
    mock_pull.draft = False
    mock_pull.labels = [mock_label]

    with open(tmp_path / "bots.json", "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "name": "CoolQBot",
                    "desc": "基于 NoneBot2 的聊天机器人",
                    "author_id": 1,
                    "homepage": "https://github.com/he0119/CoolQBot",
                    "tags": [],
                    "is_official": False,
                }
            ],
            f,
            ensure_ascii=False,
        )

    async with app.test_api() as ctx:
        adapter, bot = get_github_bot(ctx)

        handler = GithubHandler(bot=bot, repo_info=RepoInfo(owner="owner", repo="repo"))

        await resolve_conflict_pull_requests(handler, [mock_pull])

    # 测试 git 命令
    mock_subprocess_run.assert_not_called()

    # 检查文件是否正确
    check_json_data(
        plugin_config.input_config.bot_path,
        [
            {
                "name": "CoolQBot",
                "desc": "基于 NoneBot2 的聊天机器人",
                "author_id": 1,
                "homepage": "https://github.com/he0119/CoolQBot",
                "tags": [],
                "is_official": False,
            }
        ],
    )

    assert not mocked_api["homepage"].called
