'''
SublimeTodoReview
A SublimeText 3 plugin for reviewing todo (and other) comments within your code.

@author Jonathan Delgado (Initial Repo by @robcowie and ST3 update by @dnatag)
'''

import datetime
import fnmatch
import io
import itertools
import os
import re
import shutil
import sublime
import sublime_plugin
import sys
import threading
import timeit

SETTINGS = [
	"case_sensitive",
	"encoding",
	"exclude_files",
	"exclude_folders",
	"include_paths",
	"merge_global_toss_target_paths",
	"merge_global_versions",
	"navigation_backward_skip",
	"navigation_forward_skip",
	"patterns",
	"patterns_weight",
	"render_folder_depth",
	"render_header_date",
	"render_header_format",
	"render_include_folder",
	"render_maxspaces",
	"resolve_symlinks",
	"toss_target_paths",
	"version_build_step",
	"version_confirm",
	"version_deployment_folder",
	"version_deployment_prefix",
	"version_footer",
	"version_header",
	"version_major",
	"version_major_description",
	"version_minor",
	"version_minor_description",
	"version_prefix",
	"version_replacements",
	"version_suffix",
]

class Settings():
	def __init__(self, view, args):
		self.user = sublime.load_settings('TodoReview.sublime-settings')
		if not args:
			self.proj = view.settings().get('TodoReview', {})
		else:
			self.proj = args

	def get(self, key, default):
		if key not in SETTINGS:
			sublime.error_message(f"TodoReview: Invalid key [{key}] in project settings.")
		return self.proj.get(key, self.user.get(key, default))

	def to_dict(self, which = None):
		if which == 'user':
			return self.user.to_dict()
		elif which == 'proj':
			return self.proj #.to_dict()
		else:
			return {"proj": self.proj, "user": self.user.to_dict()}

class Engine():
	def __init__(self, dirpaths, filepaths, view):
		self.view = view
		self.dirpaths = dirpaths
		self.filepaths = filepaths
		if settings.get('case_sensitive', False):
			case = 0
		else:
			case = re.IGNORECASE
		patt_patterns = settings.get('patterns', {})
		patt_files = settings.get('exclude_files', [])
		patt_folders = settings.get('exclude_folders', [])
		match_patterns = '|'.join(patt_patterns.values())
		match_files = [fnmatch.translate(p) for p in patt_files]
		match_folders = [fnmatch.translate(p) for p in patt_folders]

		self.patterns = re.compile(match_patterns, case)
		self.priority = re.compile(r'\(([0-9]{1,2})\)')
		self.exclude_files = [re.compile(p) for p in match_files]
		self.exclude_folders = [re.compile(p) for p in match_folders]
		self.open = self.view.window().views()
		self.open_files = [v.file_name() for v in self.open if v.file_name()]

	def files(self):
		seen_paths = []
		for dirpath in self.dirpaths:
			dirpath = self.resolve(dirpath)
			for dirp, dirnames, filepaths in os.walk(dirpath, followlinks=True):
				if any(p.search(dirp) for p in self.exclude_folders):
					continue
				for filepath in filepaths:
					self.filepaths.append(os.path.join(dirp, filepath))
		for filepath in self.filepaths:
			p = self.resolve(filepath)
			if p in seen_paths:
				continue
			if any(p.search(filepath) for p in self.exclude_folders):
				continue
			if any(p.search(filepath) for p in self.exclude_files):
				continue
			seen_paths.append(p)
			yield p

	def extract(self, files):
		encoding = settings.get('encoding', 'utf-8')
		for p in files:
			try:
				if p in self.open_files:
					for view in self.open:
						if view.file_name() == p:
							f = []
							lines = view.lines(sublime.Region(0, view.size()))
							for line in lines:
								f.append(view.substr(line))
							break
				else:
					f = io.open(p, 'r', encoding=encoding)
				for num, line in enumerate(f, 1):
					for result in self.patterns.finditer(line):
						for patt, note in result.groupdict().items():
							if not note and note != '':
								continue
							priority_match = self.priority.search(note)
							if(priority_match):
								priority = int(priority_match.group(1))
							else:
								priority = 50
							yield {
								'file': p,
								'patt': patt,
								'note': note,
								'line': num,
								'priority': priority
							}
			except(IOError, UnicodeDecodeError):
				f = None
			finally:
				thread.increment()
				if f is not None and type(f) is not list:
					f.close()

	def process(self):
		return self.extract(self.files())

	def resolve(self, directory):
		if settings.get('resolve_symlinks', True):
			return os.path.realpath(os.path.expanduser(os.path.abspath(directory)))
		else:
			return os.path.expanduser(os.path.abspath(directory))

class Thread(threading.Thread):
	def __init__(self, engine, callback):
		self.i = 0
		self.engine = engine
		self.callback = callback
		self.lock = threading.RLock()
		threading.Thread.__init__(self)

	def run(self):
		self.start = timeit.default_timer()
		if sys.version_info < (3,0,0):
			sublime.set_timeout(self.thread, 1)
		else:
			self.thread()

	def thread(self):
		results = list(self.engine.process())
		self.callback(results, self.finish(), self.i)

	def finish(self):
		return round(timeit.default_timer() - self.start, 2)

	def increment(self):
		with self.lock:
			self.i += 1
			sublime.status_message("TodoReview: {0} files scanned".format(self.i))

class TodoReviewCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		global settings, thread, project_path
		project_path = self.view.window().extract_variables()["project_path"]
		filepaths = []
		self.args = args
		window = self.view.window()
		paths = args.get('paths', None)
		settings = Settings(self.view, args.get('settings', False))
		if args.get('current_file', False):
			if self.view.file_name():
				paths = []
				filepaths = [self.view.file_name()]
			else:
				print('TodoReview: File must be saved first')
				return
		else:
			if not paths and (paths := settings.get('include_paths', False)):
				# warning: gem's hacking here
				paths = [os.path.normpath(path) if os.path.isabs(path) else os.path.normpath(os.path.join(project_path, path)) for path in paths ]

			if args.get('open_files', False):
				filepaths = [v.file_name() for v in window.views() if v.file_name()]
			if not args.get('open_files_only', False):
				if not paths:
					paths = window.folders()
				else:
					for p in paths:
						if os.path.isfile(p):
							filepaths.append(p)
			else:
				paths = []
		engine = Engine(paths, filepaths, self.view)
		thread = Thread(engine, self.render)
		thread.start()

	def render(self, results, time, count):
		self.view.run_command('todo_review_render', {
			"results": results,
			"time": time,
			"count": count,
			"args": self.args
		})

class TodoReviewRender(sublime_plugin.TextCommand):
	def run(self, edit, results, time, count, args):
		self.args = args
		self.edit = edit
		self.time = time
		self.count = count
		self.results = results
		self.sorted = self.sort()
		self.rview = self.get_view()
		self.draw_header()
		self.draw_results()
		self.window.focus_view(self.rview)
		self.args['settings'] = settings.proj
		self.rview.settings().set('review_args', self.args)

	def sort(self):
		self.largest = 0
		for item in self.results:
			self.largest = max(len(self.draw_file(item)), self.largest)
		self.largest = min(self.largest, settings.get('render_maxspaces', 50)) + 6
		w = settings.get('patterns_weight', {})
		key = lambda m: (str(w.get(m['patt'].upper(), m['patt'])), m['priority'])
		results = sorted(self.results, key=key)
		return itertools.groupby(results, key=lambda m: m['patt'])

	def get_view(self):
		self.window = sublime.active_window()
		for view in self.window.views():
			if view.settings().get('todo_results', False):
				view.erase(self.edit, sublime.Region(0, view.size()))
				return view
		view = self.window.new_file()
		view.set_name('TodoReview')
		view.set_scratch(True)
		view.settings().set('todo_results', True)
		if sys.version_info < (3,0,0):
			view.set_syntax_file('Packages/TodoReview/TodoReview.hidden-tmLanguage')
		else:
			view.assign_syntax('Packages/TodoReview/TodoReview.hidden-tmLanguage')
		view.settings().set('line_padding_bottom', 2)
		view.settings().set('line_padding_top', 2)
		view.settings().set('word_wrap', False)
		view.settings().set('command_mode', True)
		return view

	def draw_header(self):
		forms = settings.get('render_header_format', '%d - %c files in %t secs')
		datestr = settings.get('render_header_date', '%A %m/%d/%y at %I:%M%p')
		if not forms:
			forms = '%d - %c files in %t secs'
		if not datestr:
			datestr = '%A %m/%d/%y at %I:%M%p'
		if len(forms) == 0:
			return
		date = datetime.datetime.now().strftime(datestr)
		res = '// '
		res += forms \
			.replace('%d', date) \
			.replace('%t', str(self.time)) \
			.replace('%c', str(self.count))
		res += '\n'
		self.rview.insert(self.edit, self.rview.size(), res)

	def draw_results(self):
		data = [x[:] for x in [[]] * 2]
		for patt, items in self.sorted:
			items = list(items)
			res = '\n## %t (%n)\n' \
				.replace('%t', patt.upper()) \
				.replace('%n', str(len(items)))
			self.rview.insert(self.edit, self.rview.size(), res)
			for idx, item in enumerate(items, 1):
				line = '%i. %f' \
					.replace('%i', str(idx)) \
					.replace('%f', self.draw_file(item))
				res = '%f%s%n\n' \
					.replace('%f', line) \
					.replace('%s', ' '*max((self.largest - len(line)), 1)) \
					.replace('%n', item['note'])
				start = self.rview.size()
				self.rview.insert(self.edit, start, res)
				region = sublime.Region(start, self.rview.size())
				data[0].append(region)
				data[1].append(item)
		self.rview.add_regions('results', data[0], '')
		d = dict(('{0},{1}'.format(k.a, k.b), v) for k, v in zip(data[0], data[1]))
		self.rview.settings().set('review_results', d)

	def draw_file(self, item):
		if settings.get('render_include_folder', False):
			depth = settings.get('render_folder_depth', 1)
			if depth == 'auto':
				f = item['file']
				for folder in sublime.active_window().folders():
					if f.startswith(folder):
						f = os.path.relpath(f, folder)
						break
				f = f.replace('\\', '/')
			else:
				f = os.path.dirname(item['file']).replace('\\', '/').split('/')
				f = '/'.join(f[-depth:] + [os.path.basename(item['file'])])
		else:
			f = os.path.basename(item['file'])
		return '%f:%l' \
			.replace('%f', f) \
			.replace('%l', str(item['line']))



class TodoReviewResults(sublime_plugin.TextCommand):

	def accept_version(self, new_build_number):
		builds = self.version_settings['builds']
		footer = self.version_settings['footer']
		header = self.version_settings['header']
		if new_build_number in builds:
			sublime.error_message('TodoReview: build already exists.')
			return
		copy_from = self.file_path_and_line('path')
		copy_to = self.versioned_file('path')
		version = self.versioned_file('version')
		shutil.copyfile(copy_from, copy_to)

		# adding of headers/footer
		with open(copy_to, 'r+', encoding = 'utf-8') as f_to:
			contents = f_to.read()
			# todo: take sql dialect into account
			versioned_contents = contents.format(fileversion=version)
			versioned_header = header.format(fileversion=version)
			versioned_footer = footer.format(fileversion=version)
			wrapped = f'{versioned_header}{versioned_contents}{versioned_footer}'
			# todo: implement replacements
			f_to.truncate(0)
			f_to.seek(0)
			f_to.write(wrapped)

		# version number write-back
		with open(copy_from, 'w', encoding = 'utf-8') as f_from:
			# contents = f_from.read()
			f_from.truncate(0)
			f_from.seek(0)
			f_from.write(versioned_contents)


	def versioned_file(self, part):
		build = self.version_settings['build']
		file_name = self.version_settings['file_name']
		major = self.version_settings['major']
		minor = self.version_settings['minor']
		prefix = self.version_settings['prefix']
		suffix = self.version_settings['suffix']
		version_path = self.version_settings['version_path']

		if part == 'folder':
			return version_path
		elif part == 'version':
			return f'{major}.{minor}.{build}'
		elif part == 'name':
			return f'{prefix}{major}.{minor}.{build}{suffix}{file_name}'
		elif part == 'path':
			return os.path.join(version_path, f'{prefix}{major}.{minor}.{build}{suffix}{file_name}')

	def run(self, edit, **args):
		self.settings = self.view.settings()
		self.project_path = self.view.window().extract_variables()["project_path"]

		if not self.settings.get('review_results'):
			return
		if args.get('version'):
			self.version_settings = self.validated_version_settings()
			return
			if not self.version_settings:
				return
			else:

				build_step = self.version_settings['build_step']
				confirm = self.version_settings['confirm']
				prefix = self.version_settings['prefix']
				suffix = self.version_settings['suffix']
				version_path = self.version_settings['version_path']
				self.version_settings['file_name'] = self.file_path_and_line('name')
				if not os.path.exists(version_path):
					os.makedirs(version_path)
				files = os.listdir(version_path)
				semver_pattern = re.compile(f'^{prefix}(?:(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<build>\\d+)){suffix}')
				self.version_settings['builds'] = builds = [pf.group('build') for pf in [semver_pattern.match(file) for file in files] if pf]
				if builds:
					self.version_settings['build'] = build = int(max(builds)) + build_step
				else:
					self.version_settings['build'] = build = build_zero
				new_file_name = self.versioned_file('name')

				if confirm:
					self. view.window().show_input_panel(
						f'The versioned file will be: {new_file_name}, is this corret? Override the build number if not!',
						str(build), self.accept_version, None, None)
				else:
					self.accept_version(build)
			return

		if args.get('toss'):
			target_paths = self.settings.get('toss_target_paths', None)
			if not target_paths:
				sublime.error_message("TodoReview: no toss target folder defined.")
			else:
				file_path = self.file_path_and_line('path')
				numeric_prefix_pattern = re.compile('^(\\d+)_')
				prepared_target_paths = self.prepared_target_paths(target_paths)

				for target_path in prepared_target_paths:
					if not os.path.exists(target_path):
						os.makedirs(target_path)
					files = os.listdir(target_path)
					prefixes = [pf.group(1) for pf in [numeric_prefix_pattern.match(file) for file in files] if pf]
					if prefixes:
						next_prefix = int(max(prefixes)) + 1
					else:
						next_prefix = 0
					new_file_name = f"{next_prefix}_{os.path.split(file_path)[1]}"

					target = os.path.join(target_path, new_file_name)
					if os.path.isfile(target):
						response = sublime.yes_no_cancel_dialog(f"File {target} already exists. Overwrite?")
						if response == sublime.DIALOG_CANCEL:
							return
						elif response == sublime.DIALOG_NO:
							continue
					shutil.copyfile(file_path, target)
				return
			return
		if args.get('open'):
			window = self.view.window()
			index = int(self.settings.get('selected_result', -1))
			result = self.view.get_regions('results')[index]
			coords = '{0},{1}'.format(result.a, result.b)
			i = self.settings.get('review_results')[coords]
			p = "%f:%l".replace('%f', i['file']).replace('%l', str(i['line']))
			view = window.open_file(p, sublime.ENCODED_POSITION)
			window.focus_view(view)
			return
		if args.get('refresh'):
			args = self.settings.get('review_args')
			self.view.run_command('todo_review', args)
			self.settings.erase('selected_result')
			return
		if args.get('direction'):
			d = args.get('direction')
			results = self.view.get_regions('results')
			if not results:
				return
			start_arr = {
				'down': -1,
				'up': 0,
				'down_skip': -1,
				'up_skip': 0
			}
			dir_arr = {
				'down': 1,
				'up': -1,
				'down_skip': settings.get('navigation_forward_skip', 10),
				'up_skip': settings.get('navigation_backward_skip', 10) * -1
			}
			sel = int(self.settings.get('selected_result', start_arr[d]))
			sel = sel + dir_arr[d]
			if sel == -1:
				target = results[len(results) - 1]
				sel = len(results) - 1
			if sel < 0:
				target = results[0]
				sel = 0
			if sel >= len(results):
				target = results[0]
				sel = 0
			target = results[sel]
			self.settings.set('selected_result', sel)
			region = target.cover(target)
			self.view.add_regions('selection', [region], 'selected', 'dot')
			self.view.show(sublime.Region(region.a, region.a + 5))
			return

	def validated_version_settings(self):
		number_of_errors = 0
		number_of_warnings = 0
		if not (deployment_folder := version_settings.get('deployment_folder')):
			sublime.error_message('TodoReview: no version deployment folder set.')
			number_of_errors += 1
		if not (prefix := version_settings.get('prefix')):
			sublime.error_message('TodoReview: no version prefix set.')
			number_of_errors += 1
		if not (suffix := version_settings.get('suffix')):
			sublime.error_message('TodoReview: no version suffix set.')
			number_of_errors += 1
		if not (major := version_settings.get('major')):
			sublime.error_message('TodoReview: no version major set.')
			number_of_errors += 1
		if not (major_description := version_settings.get('major_description')):
			print('TodoReview: no version major description set.')
			number_of_warnings += 1
		if not (minor := version_settings.get('minor')):
			sublime.error_message('TodoReview: no version minor set.')
			number_of_errors += 1
		if not (minor_description := version_settings.get('minor_description')):
			print('TodoReview: no version minor description set.')
			number_of_warnings += 1
		if not (replacements := version_settings.get('replacements')):
			print('TodoReview: no replacements set.')

		if number_of_errors:
			return None
		else:
			build_zero = version_settings.get('build_zero', 101)
			build_step = version_settings.get('build_step', 3)
			footer = version_settings.get('footer', '-- header: ({fileversion})')
			header = version_settings.get('header', '-- footer: ({fileversion})')
			confirm = version_settings.get('confirm', False)
			version_path = os.path.normpath(f'{major}{" - " + major_description if major_description else ""}/{minor}{" - " + minor_description if minor_description else ""}')
			deployment_folder = os.path.normpath(deployment_folder)
			if os.path.isabs(deployment_folder):
				version_path = os.path.join(deployment_folder, version_path)
			else:
				version_path = os.path.join(self.project_path, deployment_folder, version_path)
			return {
				'build': None,
				'build_step': build_step,
				'build_zero': build_zero,
				'builds': None,
				'confirm': confirm,
				'file_name': None,
				'footer': footer,
				'header': header,
				'major': major,
				'minor': minor,
				'prefix': prefix,
				'replacements': replacements,
				'suffix': suffix,
				'version_path': version_path,
			}

	def file_path_and_line(self, which_part):
		window = self.view.window()
		index = int(self.settings.get('selected_result', -1))
		result = self.view.get_regions('results')[index]
		coords = '{0},{1}'.format(result.a, result.b)
		i = self.settings.get('review_results')[coords]
		file_name = i['file']
		line = i['line']
		if which_part == 'path':
			return file_name
		elif which_part == 'name':
			return os.path.split(file_name)[1]
		elif which_part == 'folder':
			return os.path.split(file_name)[0]
		elif which_part == 'loc':
			return line
		elif which_part == 'both':
			return f"{file}:{line}"

	def prepared_target_paths(self, target_paths):
		project_path = self.view.window().extract_variables()["project_path"]
		for i, target_path in enumerate(target_paths):
			target_path = os.path.normpath(target_path)
			if not os.path.isabs(target_path):
				target_path = os.path.join(project_path, target_path)
			target_paths[i] = target_path
		return target_paths








