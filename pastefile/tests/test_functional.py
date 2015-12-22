#!/usr/bin/python


import os
from os.path import join as osjoin
import unittest
import json
from StringIO import StringIO
import shutil
os.environ['PASTEFILE_SETTINGS'] = '../pastefile-test.cfg'
os.environ['TESTING'] = 'TRUE'

import pastefile.app as flaskr


class FlaskrTestCase(unittest.TestCase):

    def clean_dir(self):
        if os.path.isdir(self.testdir):
            shutil.rmtree(self.testdir)

    def setUp(self):
        self.testdir = './tests'
        flaskr.app.config['TESTING'] = True
        self.clean_dir()
        os.makedirs(osjoin(self.testdir, 'files'))
        os.makedirs(osjoin(self.testdir, 'tmp'))
        self.app = flaskr.app.test_client()

    def tearDown(self):
        self.clean_dir()

    def test_slash(self):
        rv = self.app.get('/', headers={'User-Agent': 'curl'})
        assert 'Get infos about one file' in rv.data

    def test_ls(self):
        # Test ls without files
        rv = self.app.get('/ls', headers={'User-Agent': 'curl'})
        self.assertEquals('200 OK', rv.status)
        self.assertEquals(json.loads(rv.data), {})

        # With one posted file
        rnd_str = os.urandom(1024)
        with open(osjoin(self.testdir, 'test_file'), 'w+') as f:
            f.writelines(rnd_str)
            rv = self.app.post('/', data={'file': (f, 'test_pastefile_random.file'),})

        rv = self.app.get('/ls', headers={'User-Agent': 'curl'})
        self.assertEquals('200 OK', rv.status)
        # basic check if we have an array like {md5: {name: ...}}
        for md5, infos in json.loads(rv.data).iteritems():
                self.assertTrue('name' in infos)

        # Try with ls disables
        flaskr.app.config['DISABLE_LS'] = True
        rv = self.app.get('/ls', headers={'User-Agent': 'curl'})
        self.assertEquals(rv.data, 'Administrator disabled the /ls option.')

    def test_upload_and_retrieve(self):
        rnd_str = os.urandom(1024)
        with open(osjoin(self.testdir, 'test_file'), 'w+') as f:
            f.writelines(rnd_str)
        test_md5 = flaskr.get_md5(osjoin(self.testdir, 'test_file'))
        with open(osjoin(self.testdir, 'test_file'), 'r') as f:
            rv = self.app.post('/', data={'file': (f, 'test_pastefile_random.file'),})
        assert rv.data == "http://localhost/%s\n" % (test_md5)
        assert rv.status == '200 OK'
        rv = self.app.get("/%s" % (test_md5), headers={'User-Agent': 'curl'})
        assert rv.status == '200 OK'

if __name__ == '__main__':
    unittest.main()
