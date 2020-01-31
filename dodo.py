import glob
import subprocess
from contextlib import suppress
from pathlib import Path

from doit.action import CmdAction


PACKAGE = "efb_wechat_slave"
README_BASE = "./readme_translations/en_US.rst"
DEFAULT_BUMP_MODE = "patch"
# major, minor, patch, alpha, beta, dev, post
DOIT_CONFIG = {
    "default_tasks": ["msgfmt"]
}


def task_gettext():
    pot = f"./{PACKAGE}/locale/{PACKAGE}.pot"
    sources = glob.glob(f"./{PACKAGE}/**/*.py", recursive=True)
    sources = [i for i in sources if "__version__.py" not in i]
    command = "xgettext --add-comments=TRANSLATORS --from-code=UTF-8 -o " + pot + " " + " ".join(sources)
    sources.append(README_BASE)
    return {
        "actions": [
            command,
            ['cp', README_BASE, './.cache/README.rst'],
            ['sphinx-build', '-b', 'gettext', '-C', '-D', 'master_doc=README',
             '-D', 'gettext_additional_targets=literal-block,image',
             './.cache', './readme_translations/locale/', './.cache/README.rst'],
            ['rm', './.cache/README.rst'],
        ],
        "targets": [
            pot
        ],
        "file_dep": sources
    }


def task_msgfmt():
    languages = [i[i.rfind('/')+1:] for i in glob.glob("./readme_translations/locale/*_*")]

    with suppress(ValueError):
        languages.remove("zh_CN")
        languages.remove("en_US")

    sources = glob.glob("./**/*.po", recursive=True)
    dests = [i[:-3] + ".mo" for i in sources]
    actions = [["msgfmt", sources[i], "-o", dests[i]] for i in range(len(sources))]

    actions.append(["mkdir", "./.cache/source"])
    actions.append(["cp", README_BASE, "./.cache/source/README.rst"])
    locale_dirs = (Path('.') / "readme_translations" / "locale").absolute()
    for i in languages:
        actions.append(["sphinx-build", "-E", "-b", "rst", "-C",
                        "-D", f"language={i}", "-D", f"locale_dirs={locale_dirs}",
                        "-D", "extensions=sphinxcontrib.restbuilder",
                        "-D", "master_doc=README", "./.cache/source", f"./.cache/{i}"])
        actions.append(["mv", f"./.cache/{i}/README.rst", f"./readme_translations/{i}.rst"])
        actions.append(["rm", "-rf", f"./.cache/{i}"])
    actions.append(["rm", "-rf", "./.cache/source"])

    return {
        "actions": actions,
        "targets": dests,
        "file_dep": sources,
        "task_dep": ['crowdin', 'crowdin_pull']
    }


def task_crowdin():
    sources = glob.glob(f"./{PACKAGE}/**/*.po", recursive=True)
    sources.append("readme_translations/en_US.rst")
    return {
        "actions": ["crowdin upload sources"],
        "file_dep": sources,
        "task_dep": ["gettext"]
    }


def task_crowdin_pull():
    return {
        "actions": ["crowdin download"]
    }


def task_commit_lang_file():
    def git_actions():
        if subprocess.run(['git', 'diff-index', '--quiet', 'HEAD']).returncode != 0:
            return ['git commit -S -m "loc: sync localization files from crowdin"']
        return ["echo"]

    return {
        "actions": [
            ["git", "add", "*.po", "readme_translations/*.rst"],
            CmdAction(git_actions)
        ],
        "task_dep": ["crowdin", "msgfmt"]
    }


def task_bump_version():
    def gen_bump_version(mode=DEFAULT_BUMP_MODE):
        return './bump.py --tag ' + mode

    return {
        "actions": [CmdAction(gen_bump_version)],
        "params": [
            {
                "name": "mode",
                "short": "b",
                "long": "bump",
                "default": DEFAULT_BUMP_MODE,
                "help": "{major}.{minor}.{patch}{(a|b)}{.post}{.dev}",
                "choices": [
                    ("major", "Bump a major version"),
                    ("minor", "Bump a minor version"),
                    ("patch", "Bump a patch version"),
                    ("alpha", "Bump to the next alpha version"),
                    ("alpha", "Bump to the next beta version"),
                    ("post", "Bump to the next post version"),
                    ("dev", "Bump a dev version (for commit only)")
                ]
            }
        ],
        "task_dep": ["mypy", "test", "commit_lang_file"]
    }


def task_mypy():
    actions = [f"mypy -p {PACKAGE} --ignore-missing-imports"]
    sources = glob.glob(f"./{PACKAGE}/**/*.py", recursive=True)
    sources = [i for i in sources if "__version__.py" not in i]
    return {
        "actions": actions,
        "file_dep": sources
    }


def task_test():
    sources = glob.glob(f"./{PACKAGE}/**/*.py", recursive=True)
    sources = [i for i in sources if "__version__.py" not in i]
    return {
        "actions": [
            f"coverage run --source ./{PACKAGE} -m pytest",
            "coverage report"
        ],
        "file_dep": sources
    }


def task_build():
    return {
        "actions": [
            f"mv {PACKAGE}.egg-info {PACKAGE}.egg-info.bak",
            "python setup.py sdist bdist_wheel",
            f"rm -rf build {PACKAGE}.egg-info",
            f"mv {PACKAGE}.egg-info.bak {PACKAGE}.egg-info",
        ],
        "task_dep": ["mypy", "test", "msgfmt", "bump_version"]
    }


def task_publish():
    def get_twine_command():
        __version__ = __import__(PACKAGE).__version__
        if 'dev' in __version__:
            raise ValueError(f"Cannot publish dev version ({__version__}).")
        binarys = glob.glob(f"./dist/*{__version__}*", recursive=True)
        return " ".join(["twine", "upload"] + binarys)
    return {
        "actions": [CmdAction(get_twine_command)],
        "task_dep": ["build"]
    }
