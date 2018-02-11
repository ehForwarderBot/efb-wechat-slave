PACKAGE = efb_wechat_slave

gettext:
	find ./$(PACKAGE) -iname "*.py" | xargs xgettext -o ./$(PACKAGE)/locale/$(PACKAGE).pot

crowdin: gettext
	find "$(CURDIR)" -iname '*.po' -exec bash -c 'msgfmt "$$0" -o "$${0%.po}.mo"' {} \;
	crowdin push

crowdin-pull:
	crowdin pull
	find "$(CURDIR)" -iname '*.po' -exec bash -c 'msgfmt "$$0" -o "$${0%.po}.mo"' {} \;

publish:
	python setup.py sdist bdist_wheel upload --sign --show-response

pre-release: crowdin crowdin-pull
	git add \*.po
	git commit -m 'Sync localization files from Crowdin'
