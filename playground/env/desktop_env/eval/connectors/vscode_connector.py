import os
import shutil
from enum import Enum

import requests
from requests.adapters import HTTPAdapter, Retry


class FilterType(Enum):
    """
    Filter type for marketplace search
    """
    Tag = 1
    ExtensionId = 4
    Category = 5
    ExtensionName = 7
    Target = 8
    Featured = 9
    SearchText = 10
    ExcludeWithFlags = 12


class SortBy(Enum):
    """
    Result sorting options for marketplace search
    """
    NoneOrRelevance = 0
    LastUpdatedDate = 1
    Title = 2
    PublisherName = 3
    InstallCount = 4
    PublishedDate = 10
    AverageRating = 6
    WeightedRating = 12


class SortOrder(Enum):
    """
    Sort order for marketplace search
    """
    Default = 0
    Ascending = 1
    Descending = 2


# TODO: maybe merge this to desktop_env/eval/vscode_evaluator/vscode_evaluator.py
class VSCodeConnector:
    def __init__(
        self,
        workspace_path: str,
        executable_path: str = "code",
    ) -> None:
        self.executable_path = executable_path
        self.workspace_path = workspace_path
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def marketplace_search(
        self,
        query: list[dict],
        sort_by: SortBy,
        sort_order: SortOrder,
    ):
        """
        Search for extensions in the marketplace

        Args:
            query (list[dict]): List of query filters
            sort_by (SortBy): Sort by option
            sort_order (SortOrder): Sort order option

        Returns:
            list: List of extensions

        Example::

            query = [
                        {
                            "filterType": FilterType.ExtensionName.value,
                            "value": "DavidAnson.vscode-markdownlint"
                        },
                    ]
        """
        extension_list = []
        for extension in self.get_vscode_extensions(
            session=self.session,
            query=query,
            sort_by=sort_by,
            sort_order=sort_order,
        ):
            extension_list.append(extension)
        return extension_list

    def marketplace_search_by_extension_id(
        self,
        extension_name: str,
    ):
        """
        Search by extension name
        Default sort by install count descending
        """
        return self.marketplace_search(
            query=[
                {"filterType": FilterType.ExtensionName.value, "value": extension_name},
            ],
            sort_by=SortBy.InstallCount,
            sort_order=SortOrder.Descending,
        )

    def marketplace_search_by_keyword(
        self,
        keyword: str,
    ):
        """
        Search by keyword
        Default sort by install count descending
        """
        return self.marketplace_search(
            query=[
                {"filterType": FilterType.SearchText.value, "value": keyword},
            ],
            sort_by=SortBy.InstallCount,
            sort_order=SortOrder.Descending,
        )

    def update_settings(self, settings: str) -> None:
        with open(
            os.path.join(self.workspace_path, ".vscode", "settings.json"), "w"
        ) as f:
            f.write(settings)

    def compare_settings(self, settings: str) -> bool:
        with open(
            os.path.join(self.workspace_path, ".vscode", "settings.json"), "r"
        ) as f:
            current_settings = f.read()
        return current_settings == settings

    def reset_settings(self) -> None:
        shutil.rmtree(os.path.join(self.workspace_path, ".vscode"))

    def list_extensions(self) -> dict:
        # if extension_list is not None:
        #     if versions:
        #         return [extension.split("@")[0] for extension in extension_list]
        #     else:
        #         return extension_list
        # else:
        extension_list = (
            os.popen(f"{self.executable_path} --list-extensions --show-versions")
            .read()
            .strip()
            .split("\n")
        )
        return {
            extension.split("@")[0]: extension.split("@")[1]
            for extension in extension_list
        }

    def uninstall_all_extensions(self) -> bool:
        # TODO: For safety reasons, disable this method now.
        assert False, "This method is not implemented yet"
        os.system(f"{self.executable_path} --uninstall-extension '*'")
        return self.list_extensions() == {}

    def install_extension(self, extension_name: str) -> bool:
        os.system(f"{self.executable_path} --install-extension {extension_name}")
        return extension_name in self.list_extensions()

    def uninstall_extension(self, extension_name: str) -> bool:
        if "@" in extension_name:
            extension_name = extension_name.split("@")[0]
        if extension_name in self.list_extensions():
            os.system(f"{self.executable_path} --uninstall-extension {extension_name}")
            return extension_name not in self.list_extensions()
        else:
            return True

    def extension_installed(self, extension_name: str) -> bool:
        return extension_name in self.list_extensions()

    @staticmethod
    def get_vscode_extensions(
        session: requests.Session,
        query: list,
        max_page: int = 2,
        page_size: int = 10,
        sort_by: SortBy = SortBy.InstallCount,
        sort_order: SortOrder = SortOrder.Descending,
        include_versions: bool = True,
        include_files: bool = True,
        include_category_and_tags: bool = True,
        include_shared_accounts: bool = True,
        include_version_properties: bool = True,
        exclude_non_validated: bool = True,
        include_installation_targets: bool = True,
        include_asset_uri: bool = True,
        include_statistics: bool = True,
        include_latest_version_only=False,
        unpublished: bool = True,
        include_name_conflict_info: bool = True,
        api_version: str = "7.2-preview.1",
    ):
        """
        https://gist.github.com/jossef/8d7681ac0c7fd28e93147aa5044bc129
        """

        headers = {
            "Accept": f"application/json; charset=utf-8; api-version={api_version}"
        }

        flags = 0
        if include_versions:
            flags |= 0x1

        if include_files:
            flags |= 0x2

        if include_category_and_tags:
            flags |= 0x4

        if include_shared_accounts:
            flags |= 0x8

        if include_version_properties:
            flags |= 0x10

        if exclude_non_validated:
            flags |= 0x20

        if include_installation_targets:
            flags |= 0x40

        if include_asset_uri:
            flags |= 0x80

        if include_statistics:
            flags |= 0x100

        if include_latest_version_only:
            flags |= 0x200

        if unpublished:
            flags |= 0x1000

        if include_name_conflict_info:
            flags |= 0x8000

        for page in range(1, max_page + 1):
            body = {
                "filters": [
                    {
                        "criteria": [
                            {
                                "filterType": FilterType.Target.value,
                                "value": "Microsoft.VisualStudio.Code",
                            },
                            *query,
                        ],
                        "pageNumber": page,
                        "pageSize": page_size,
                        "sortBy": sort_by.value,
                        "sortOrder": sort_order.value,
                    }
                ],
                "assetTypes": [],
                "flags": flags,
            }

            r = session.post(
                (
                    "https://marketplace.visualstudio.com/"
                    "_apis/public/gallery/extensionquery"
                ),
                json=body,
                headers=headers,
            )
            r.raise_for_status()
            response = r.json()

            extensions = response["results"][0]["extensions"]
            for extension in extensions:
                yield extension

            if len(extensions) != page_size:
                break
