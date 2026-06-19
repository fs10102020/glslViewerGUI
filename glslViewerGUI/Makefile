PREFIX ?= $(HOME)/.local
BINDIR ?= $(PREFIX)/bin
APPDIR ?= $(PREFIX)/share/applications
DATADIR ?= $(PREFIX)/share/glslviewer-gui

.PHONY: all install uninstall run clean

all:
	@echo "Targets: run, install, uninstall"

run:
	cd glslViewerGUI && python3 main.py

install:
	install -d $(BINDIR) $(APPDIR) $(DATADIR)
	cp -r glslViewerGUI/* $(DATADIR)/
	chmod +x $(DATADIR)/glslviewer-gui
	ln -sf $(DATADIR)/glslviewer-gui $(BINDIR)/glslviewer-gui
	cp glslViewerGUI/glslviewer-gui.desktop $(APPDIR)/
	@echo "Installed to $(PREFIX)"

uninstall:
	rm -rf $(DATADIR)
	rm -f $(BINDIR)/glslviewer-gui
	rm -f $(APPDIR)/glslviewer-gui.desktop
	@echo "Uninstalled from $(PREFIX)"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
