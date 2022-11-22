# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


import asyncio
import random

# -- Project information -----------------------------------------------------
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import List
import re

import aiohttp
import aiofiles
import yaml
from lxml import etree
from sphinx.application import Sphinx
from sphinx.util import logging
import os

LOGGER = logging.getLogger("conf")

project = "yanglab-guide"
author = "Yangang Li"
copyright = f"{datetime.now().year}, yanglab"

# The full version, including alpha/beta/rc tags
release = "1.0"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
    # "sphinx_tabs.tabs",
    "sphinx_thebe",
    "sphinx_togglebutton",
    "sphinxcontrib.bibtex",
    "sphinxcontrib.youtube",
    "sphinxext.opengraph",
]

myst_enable_extensions = [
    "amsmath",
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

intersphinx_mapping = {
    "mypy": ("https://mypy.readthedocs.io/en/stable/", None),
    "python": ("https://docs.python.org/3.8", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
}
source_suffix = [".rst", ".md"]
language = "en"
linkcheck_ignore = [
    "codeofconduct.html",
]
# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_book_theme"
html_title = "Lab Guide For Yang Lab"
html_copy_source = True
html_theme_options = {
    "repository_url": "https://github.com/ylab-hi/yanglab-guide",
    "use_repository_button": True,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_logo = "_static/logo.png"

html_theme_options = {
    "path_to_docs": "source",
    "repository_url": "https://github.com/ylab-hi/yanglab-guide",
    # "repository_branch": "gh-pages",  # For testing
    "launch_buttons": {
        "binderhub_url": "https://mybinder.org",
        "colab_url": "https://colab.research.google.com/",
        "deepnote_url": "https://deepnote.com/",
        "notebook_interface": "jupyterlab",
        "thebe": True,
        # "jupyterhub_url": "https://datahub.berkeley.edu",  # For testing
    },
    "use_edit_page_button": True,
    "use_issues_button": True,
    "use_repository_button": True,
    "use_download_button": True,
    "logo_only": True,
    "show_toc_level": 2,
    # "announcement": (
    #     "⚠️The Lab Guide of Yang Lab, "
    #     "so double-check your custom CSS rules!⚠️"
    # ),
    # For testing
    # "use_fullscreen_button": False,
    # "home_page_in_toc": True,
    # "single_page": True,
    # "extra_footer": "<a href='https://google.com'>Test</a>",  # DEPRECATED KEY
    # "extra_navbar": "<a href='https://google.com'>Test</a>",
    # "show_navbar_depth": 2,
}

bibtex_bibfiles = ["references.bib"]

GITHUB_URL = "https://raw.githubusercontent.com/ylab-hi/yanglab-guide/main"


def get_cover_images(items):
    asyncio.run(_get_cover_images(items))


async def download(url, name, headers, session: aiohttp.ClientSession) -> None:
    """Download a file from `url` and save it locally under `local_filename`."""
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                async with aiofiles.open(
                    f"source/_static/covers/{name.replace(' ', '_')}.jpg", "wb"
                ) as f:
                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                        await asyncio.sleep(0.001)
                        await f.write(chunk)
            else:
                raise RuntimeError(
                    f"Cannot download {url} with status code {resp.status}"
                )
    except Exception as e:
        LOGGER.error(f"Cannot download {url}: {e}")


async def _get_cover_images(items):
    timeout = aiohttp.client.ClientTimeout(2 * 60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = []
        for item in items:
            image_path = Path(
                f"source/_static/covers/{item['name'].replace(' ', '_')}.jpg"
            )
            if not image_path.exists():
                tasks.append(_get_cover_image_worker(item, session))
            else:
                item["image"] = f"{GITHUB_URL}/{image_path}"
        await asyncio.gather(*tasks)


async def _get_cover_image_worker(item, session):
    default_cover = "https://raw.githubusercontent.com/ylab-hi/yanglab-guide/main/source/_static/book.svg"
    base_domain = "https://www.goodreads.com"
    search_domain = base_domain + "/search/"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 "
        "Safari/537.36",
        "Connection": "keep-alive",
    }

    title = item["name"]
    first_num = 2
    async with session.get(search_domain, params={"q": title}, headers=headers) as resp:
        try:
            resp.raise_for_status()
        except Exception as e:
            LOGGER.info(f"Failed to fetch {title} cover using default\n{e.args}")
            item["image"] = default_cover
        else:
            tree = etree.HTML(await resp.text())

            cover_urls: List[str] = tree.xpath(
                f"//table[@class='tableList']//tr[position()<{first_num}]//a[@class='bookTitle']/@href"
            )
            names: List[str] = tree.xpath(
                f"//table[@class='tableList']//tr[position()<{first_num}]//td/a/@title"
            )
            assert len(cover_urls) == len(names)

            # fetch the first one
            cover = await _fetch_image(session, base_domain + cover_urls[0], headers)

            if not cover:
                LOGGER.info(f"Failed to fetch {title} cover using default")
                item["image"] = default_cover
            else:

                if (
                    os.environ.get("READTHEDOCS") is None
                    and os.environ.get("GITHUB_ACTIONS") is None
                ):
                    # local build
                    await download(cover[0], title, headers, session)
                    LOGGER.info(f"Successfully fetched {title} cover {cover[0]}")
                    item[
                        "image"
                    ] = f'{GITHUB_URL}/source/_static/covers/{title.replace(" ", "_")}.jpg'
                else:
                    # doesn't use  local image in read the docs
                    item["image"] = cover[0]


async def _fetch_image(session, url, header):
    cover = []
    async with session.get(url, headers=header) as resp:
        try:
            resp.raise_for_status()
        except Exception as e:
            LOGGER.info(f"Failed to fetch image cover from {url} \n{e.args}")
            return cover
        else:
            t = await resp.text()
            tree = etree.HTML(t)
            cover.extend(tree.xpath("//img[@id='coverImage']/@src"))

            if not cover:
                pat = re.compile(r"<img id=\"coverImage\" .+? src=\"(.+)\" />")
                cover.extend(re.findall(pat, t))
            return cover


def build_gallery(app: Sphinx):
    # Build the gallery file
    LOGGER.info("building gallery...")
    star = "⭐"
    grid_items = []
    books = yaml.safe_load((Path(app.srcdir) / "library.yml").read_text())
    amazon_domain = "https://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%3Dstripbooks&field-keywords="
    random.shuffle(books)

    get_cover_images(books)

    for item in books:
        star_num = 1 if not item.get("star") else int(item["star"])
        star_text = (
            f"![Star](https://img.shields.io/badge/Recommend-{star_num * star}-green)"
        )

        grid_items.append(
            f"""\
        `````{{grid-item-card}} {" ".join(item["name"].split())}
        :text-align: center
        <a href="{amazon_domain + item['name']}" target='_blank'>
        <img src="{item["image"]}" alt="logo" loading="lazy" style="max-width: 100%; max-height: 350px; margin-top: 1rem;" /> </a>
        +++

        ````{{grid}} 2 2 2 2
        :margin: 0 0 0 0
        :padding: 0 0 0 0
        :gutter: 1

        ```{{grid-item}}
        :child-direction: row
        :child-align: end
        {star_text}
        ```

        ````

        `````
        """
        )
    grid_items = "\n".join(grid_items)

    # :column: text-center col-6 col-lg-4
    # :card: +my-2
    # :img-top-cls: w-75 m-auto p-2
    # :body: d-none
    panels = f"""
![books](https://img.shields.io/badge/Total%20Books-{len(books)}-red?style=for-the-badge&logo=gitbook)
``````{{grid}} 1 2 3 3
:gutter: 1 1 2 2
:class-container: full-width
{dedent(grid_items)}
``````
    """
    (Path(app.srcdir) / "gallery.txt").write_text(panels)


def setup(app: Sphinx):
    app.add_css_file("custom.css")
    app.connect("builder-inited", build_gallery)
