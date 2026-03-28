# UP BlackboardSync
### Automatic Downloads Of Your Blackboard Content
Fork maintained for Universidad del Pacifico (Peru) by [`johnbarraza/UPBlackboardSync`](https://github.com/johnbarraza/UPBlackboardSync).
[![Get on PyPI][pypi-shield]][pypi] [![License: GPL  v2][license-shield]][gnu] [![Build][build-shield]][actions] [![GitHub Downloads][downloads-shield]][releases] [![Latest Release Downloads][release-downloads-shield]][stable] [![Latest Release][latest-shield]][stable] [![GitHub Stars][stars-shield]][stars] [![Matrix][matrix-shield]][matrix]

**BlackboardSync** performs a periodic,
incremental download of all your Blackboard content,
such as lecture slides, lab sheets, and other attachments.

<div align="center">
	<img src="https://github.com/sanjacob/BlackboardSync/assets/52013991/b7414212-034a-42a6-ab20-bb51394d885e"
         height="auto" width="75%" />
</div>
</br>

[Join the Matrix room to hear about updates, ask for help, and more!][matrix]

## About

Being a student in this day and age means constantly having to
keep up to date with the files that are uploaded to the student portal.
I needed a tool that would take care of retrieving these files for me,
allowing me to focus on the work to be done.
Something I could set up and forget about.

What I was looking for in such an application was:

- Automatic syncing with minimal intervention after the initial setup
- Graphical interface
- Cross-platform compatibility
- It would make use of the [Blackboard REST API][blackboard-api]

### [60+ Universities](UNIVERSITIES.md) Supported Around the World

**Why is my university/college not supported?**

To provide support for a specific university, it is necessary to have
some knowledge about its login process.

If you would like to help to add support for your university,
or would like to see which universities are currently supported,
[start here.](UNIVERSITIES.md)

**Built with:**

- [Python 3.11][python]
- [PyQt6][pyqt]


## Features

- Supported content:
  - Attachments of any* type (e.g. .docx, .pptx, .pdf, etc.)
  - Internet links
  - Content descriptions (saved as html files)
- Cross-platform
  - Linux, Windows, and macOS ready

*: Except videos


## Installation

#### Microsoft Store

<a href="https://apps.microsoft.com/detail/9NSXZGKPNX2H?cid=github-readme&mode=mini">
	<img src="https://get.microsoft.com/images/en-us%20dark.svg" width="200"/>
</a>

#### Flathub

<a href="https://flathub.org/apps/app.bbsync.BlackboardSync">
  <img alt="Download on Flathub"
       src="https://flathub.org/api/badge?svg&locale=en" width="200"/>
</a>

#### Windows (.exe) and MacOS (.dmg)

Please first download the [latest release][stable].

**MacOS Installation**

You will need to confirm the installation in `System Preferences > Security and Privacy`.
You can see the specific steps in the GIF below.
After the program has been installed, you may eject the mounted disk.


#### PyPI

```bash
python3 -m pip install blackboardsync
blackboardsync
```

#### From source

##### Requires [Python >=3.10, pip][python], [pipenv][pipenv], [git][git]

```bash
git clone https://github.com/johnbarraza/UPBlackboardSync.git
cd BlackboardSync
pipenv install
pipenv run python -m blackboard_sync
```

#### Previous Releases

You can find all releases on [GitHub][releases].

## Release Workflows

Releases are created by GitHub Actions workflows:

- Desktop app release workflow: [build.yml][desktop-workflow]
  - Trigger: push tag like `0.20.0` or `0.20.0-rc.1`
  - Output: desktop artifacts (`.exe`, `.dmg`) and GitHub Release assets
- Extension assets for desktop releases: [release-extension-assets.yml][ext-assets-workflow]
  - Trigger: same desktop tags (`0.20.0`, `0.20.0-rc.1`, etc.)
  - Output: Chrome (`.zip`) and Firefox (`.xpi`) extension files attached to the same release
- Browser extension release workflow: [release-extension.yml][ext-workflow]
  - Trigger: push tag like `ext-v0.1.0`
  - Output: `blackboardsync-extension-chrome-<version>.zip` and `blackboardsync-extension-firefox-<version>.xpi` as GitHub Release assets

Download counters are shown in the `GitHub Downloads` badge above and update automatically from GitHub release stats.


## Contributions

Contributions are welcome.

More details available at [CONTRIBUTING.md](CONTRIBUTING.md)

**We are looking for beta testers for all platforms!**

##### Bugs, issues or feature requests?

Open a GitHub issue [here][issues].




## License

[![License: GPL  v2][license-shield]][gnu]

This software is distributed under the [General Public License v2.0][license],
more information available at the [Free Software Foundation][gnu].


## Acknowledgements

[Blackboard API documentation][blackboard-api]

[PyInstaller][pyinstaller]

README templates/guide by [tonycrosby-tech][tonycrosby], [neildrew][neildrew],
and [Rita Lyczywek][bulldogjob]

Flathub team for their quick work in approving the app :heart:


<!-- Dependencies -->

[git]: https://git-scm.com/	"Git"
[python]: https://www.python.org/ "Python.org"
[pipenv]: https://pipenv.pypa.io/en/latest/ "Pipenv"
[pyqt]: https://pypi.org/project/PyQt6/	"Python Bindings for Qt 6"

<!-- Chat -->

[matrix]: https://matrix.to/#/#blackboardsync:matrix.org
[matrix-shield]: https://img.shields.io/matrix/blackboardsync%3Amatrix.org?logo=matrix
[actions]: https://github.com/johnbarraza/UPBlackboardSync/actions
[build-shield]: https://img.shields.io/github/actions/workflow/status/johnbarraza/UPBlackboardSync/build.yml?branch=main&label=build
[desktop-workflow]: https://github.com/johnbarraza/UPBlackboardSync/blob/main/.github/workflows/build.yml
[ext-assets-workflow]: https://github.com/johnbarraza/UPBlackboardSync/blob/main/.github/workflows/release-extension-assets.yml
[ext-workflow]: https://github.com/johnbarraza/UPBlackboardSync/blob/main/.github/workflows/release-extension.yml
[downloads-shield]: https://img.shields.io/github/downloads/johnbarraza/UPBlackboardSync/total?label=github%20downloads
[release-downloads-shield]: https://img.shields.io/github/downloads/johnbarraza/UPBlackboardSync/latest/total?label=latest%20release%20downloads
[latest-shield]: https://img.shields.io/github/v/release/johnbarraza/UPBlackboardSync?display_name=tag
[stars-shield]: https://img.shields.io/github/stars/johnbarraza/UPBlackboardSync?style=social
[stars]: https://github.com/johnbarraza/UPBlackboardSync/stargazers

<!-- Packages -->

[pypi]: https://pypi.org/project/blackboardsync
[pypi-shield]: https://img.shields.io/pypi/v/BlackboardSync?color=%23241F21
[stable]: https://github.com/johnbarraza/UPBlackboardSync/releases/latest
[releases]: https://github.com/johnbarraza/UPBlackboardSync/releases
[issues]: https://github.com/johnbarraza/UPBlackboardSync/issues


<!-- Licence -->

[license]: LICENSE "General Public License"
[gnu]: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html "Free Software Foundation"
[license-shield]: https://img.shields.io/github/license/johnbarraza/UPBlackboardSync?color=%23241F21

<!-- Acknowledgements & README Templates -->

[blackboard-api]: https://developer.blackboard.com/portal/displayApi	"Blackboard API Reference"
[pyinstaller]: https://www.pyinstaller.org/	"PyInstaller"

[tonycrosby]: https://gist.github.com/tonycrosby-tech/c18c2b6c74900c6080fc097ca0718839	"tonycrosby-tech README template"
[neildrew]: https://github.com/othneildrew/Best-README-Template	"othneildrew README template"
[bulldogjob]: https://bulldogjob.com/news/449-how-to-write-a-good-readme-for-your-github-project	"bulldogjob README guide"
