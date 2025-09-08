.PHONY: build test
SCHEME=AutoDevApp
DEST='platform=iOS Simulator,name=iPhone 15'

build:
	xcodebuild -scheme $(SCHEME) -destination $(DEST) build

test:
	xcodebuild -scheme $(SCHEME) -destination $(DEST) -enableCodeCoverage YES test
