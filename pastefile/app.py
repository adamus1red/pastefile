#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from flask import Flask, request, abort, jsonify
from flask import render_template
from pastefile import utils
from pastefile import controller

app = Flask("pastefile")
LOG = app.logger
LOG.setLevel(logging.DEBUG)
hdl_stream = logging.StreamHandler()
hdl_stream.setLevel(logging.INFO)
formatter_stream = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
hdl_stream.setFormatter(formatter_stream)
LOG.addHandler(hdl_stream)


def init_default_configuration(_app):
    _app.config.setdefault('UPLOAD_FOLDER', "/opt/pastefile/files")
    _app.config.setdefault('FILE_LIST', "/opt/pastefile/uploaded_files_jsondb")
    _app.config.setdefault('TMP_FOLDER', "/opt/pastefile/tmp")
    _app.config.setdefault('EXPIRE',  "86400")
    _app.config.setdefault('DEBUG_PORT',  "5000")
    _app.config.setdefault('LOG', "/opt/pastefile/pastefile.log")
    _app.config.setdefault('DISABLED_FEATURE', [])
    _app.config.setdefault('DISPLAY_FOR', ['chrome', 'firefox'])


def init_check_directories(_app):
    for key in ["UPLOAD_FOLDER", "FILE_LIST", "TMP_FOLDER", "LOG"]:
        directory = _app.config[key].rstrip('/')
        if not os.path.isdir(os.path.dirname(directory)):
            LOG.error("'%s' doesn't exist or is not a directory" % os.path.dirname(directory))
            return False

    for key in ["UPLOAD_FOLDER", "TMP_FOLDER"]:
        directory = _app.config[key].rstrip('/')
        if os.path.exists(directory):
            continue
        LOG.warning("'%s' doesn't exist, creating" % directory)
        try:
            os.makedirs(directory)
        except OSError as e:
            LOG.error("%s" % e)
            return False

    return True


# Set default configuration values
init_default_configuration(_app=app)


try:
    app.config.from_envvar('PASTEFILE_SETTINGS')
    app.config['instance_path'] = app.instance_path
except RuntimeError:
    LOG.error('PASTEFILE_SETTINGS envvar is not set')
    exit(1)


try:
    if os.environ['TESTING'] == 'TRUE':
        hdl_file = logging.FileHandler(filename=app.config['LOG'])
        hdl_file.setLevel(logging.DEBUG)
        formatter_file = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        hdl_file.setFormatter(formatter_file)
        LOG.addHandler(hdl_file)
    else:
        # check dirs only in non testing mode
        if not init_check_directories(_app=app):
            exit(1)
except KeyError:
    pass

LOG.warning("===== Running config =====")
for c,v in app.config.iteritems():
  LOG.warning("%s: %s" % (c,v))

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        controller.clean_files(dbfile=app.config['FILE_LIST'],
                               expire=app.config['EXPIRE'])
        return controller.upload_file(request=request, config=app.config)
    else:
        # In case no file, return help
        return abort(404)


@app.route('/<id_file>/infos', methods=['GET'])
def display_file_infos(id_file):
    file_infos = controller.get_file_info(id_file=id_file,
                                          config=app.config,
                                          env=request.environ)
    if not file_infos:
        return abort(404)
    return jsonify(file_infos)


@app.route('/<id_file>', methods=['GET', 'DELETE'])
def get_or_delete_file(id_file):
    if request.method == 'GET':
        return controller.get_file(request=request,
                                   id_file=id_file,
                                   config=app.config)
    if request.method == 'DELETE':
        try:
            if 'delete' in app.config['DISABLED_FEATURE']:
                LOG.info("[delete] Tried to call delete but this url is disabled")
                return 'Administrator disabled the delete option.\n'
        except (KeyError, TypeError):
            pass
        return controller.delete_file(request=request,
                                      id_file=id_file,
                                      dbfile=app.config['FILE_LIST'])


@app.route('/ls', methods=['GET'])
def list_all_files():
    try:
        if 'ls' in app.config['DISABLED_FEATURE']:
            LOG.info("[LS] Tried to call /ls but this url is disabled")
            return 'Administrator disabled the /ls option.\n'
    except (KeyError, TypeError):
        pass

    controller.clean_files(dbfile=app.config['FILE_LIST'],
                           expire=app.config['EXPIRE'])

    return jsonify(controller.get_all_files(request=request, config=app.config))


@app.errorhandler(404)
def page_not_found(e):
    # request.method == 'GET'
    base_url = utils.build_base_url(env=request.environ)

    helps = (
      ("Upload a file:", "curl %s -F file=@**filename**" % base_url),
      ("View all uploaded files:", "curl %s/ls" % base_url),
      ("Get infos about one file:", "curl %s/**file_id**/infos" % base_url),
      ("Get a file:", "curl -JO %s/**file_id**" % base_url),
      ("Delete a file:", "curl -XDELETE %s/**id**" % base_url),
      ("Create an alias for cli usage", 'pastefile() { curl -F file=@"$1" %s; }' % base_url),
    )
    context = {'user_agent': request.headers.get('User-Agent', ''),
               'helps': helps}
    return render_template('404.html', **context), 404
