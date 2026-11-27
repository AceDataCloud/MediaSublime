import html
import http.client
import os
import webbrowser

import sublime
import sublime_plugin

from . import media_tasks


SETTINGS = 'AceMediaTasks.sublime-settings'
SETUP = 'https://platform.acedata.cloud/console/applications?utm_source=sublime-text&utm_medium=referral&utm_campaign=evergreen'
PACKAGE = __name__.split('.')[0]


class ServiceInput(sublime_plugin.ListInputHandler):
    def name(self):
        return 'service'

    def list_items(self):
        return [(name, slug) for slug, (name, _, _) in media_tasks.SERVICES.items()]

    def preview(self, value):
        if value not in media_tasks.SERVICES:
            return ''
        name, kind, _ = media_tasks.SERVICES[value]
        return sublime.Html('<body><img width="32" height="32" src="res://Packages/{}/icons/{}.png"> '
                            '<strong>{}</strong><p>Insert an existing {} task result.</p></body>'.format(
                                html.escape(PACKAGE), value, html.escape(name), kind))


class TaskIdInput(sublime_plugin.TextInputHandler):
    def __init__(self, selection):
        self.selection = selection

    def name(self):
        return 'task_id'

    def placeholder(self):
        return 'Existing task ID'

    def initial_text(self):
        return self.selection

    def validate(self, value):
        return bool(value.strip())


class AceMediaInsertTaskCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        return not self.view.is_read_only() and len(self.view.sel()) == 1

    def input(self, args):
        if 'service' not in args:
            return ServiceInput()
        if 'task_id' not in args:
            selection = self.view.sel()[0]
            return TaskIdInput(self.view.substr(selection).strip() if selection.size() <= 150 else '')

    def run(self, edit, service, task_id):
        task_id = task_id.strip()
        if service not in media_tasks.SERVICES or not task_id or not self.is_enabled():
            return
        credentials = sublime.load_settings(SETTINGS).get('service_tokens') or {}
        if not isinstance(credentials, dict):
            sublime.error_message('Ace Media Tasks: service_tokens must be a JSON object.')
            return
        token = credentials.get(service) or os.environ.get('ACEDATACLOUD_API_TOKEN')
        if not isinstance(token, str) or not token.strip():
            sublime.error_message('Ace Media Tasks: configure a token for {} in Preferences → Package Settings → Ace Media Tasks.'.format(media_tasks.SERVICES[service][0]))
            return
        if any(char in token.strip() for char in '\r\n'):
            sublime.error_message('Ace Media Tasks: the token must be a single line.')
            return
        revision = self.view.change_count()
        selection = self.view.sel()[0]
        view = self.view

        def choose(links):
            window = view.window() if view.is_valid() else None
            if not window:
                return
            def insert(index):
                if index >= 0 and view.is_valid():
                    view.run_command('ace_media_insert_result', {
                        'a': selection.begin(), 'b': selection.end(), 'revision': revision,
                        'content': media_tasks.markdown(service, index, links[index]),
                    })
            if len(links) == 1:
                insert(0)
            else:
                window.show_quick_panel([[media_tasks.SERVICES[service][0] + ' result ' + str(i + 1), url]
                                         for i, url in enumerate(links)], insert)

        def fetch():
            try:
                record = media_tasks.retrieve(service, task_id, token.strip())
                links = media_tasks.media_links(service, task_id, record)
            except (OSError, ValueError, http.client.HTTPException) as error:
                message = str(error)
                sublime.set_timeout(lambda: sublime.error_message('Ace Media Tasks: ' + message))
            else:
                sublime.set_timeout(lambda: choose(links))
        sublime.status_message('Ace Media Tasks: retrieving the existing task…')
        sublime.set_timeout_async(fetch)


class AceMediaInsertResultCommand(sublime_plugin.TextCommand):
    def run(self, edit, a, b, revision, content):
        if self.view.is_read_only() or self.view.change_count() != revision:
            sublime.status_message('Ace Media Tasks: the document changed. Run the command again.')
            return
        self.view.replace(edit, sublime.Region(a, b), content)


class AceMediaOpenApplicationsCommand(sublime_plugin.WindowCommand):
    def run(self):
        webbrowser.open(SETUP)
