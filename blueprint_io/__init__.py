import cfg
import json
import logging
import urlparse

import http

from blueprint import git
from blueprint import Blueprint
from blueprint import context_managers

server = cfg.server()

def pull(url):
    """
    Pull a blueprint from the specified URL
    """
    
    # GET /secret/name
    # Fetch the JSON representation of the blueprint name.
    # 
    # Parameters:
    # secret: a 64-byte identifier containing numbers, letters, underscores, and dashes.
    # name: a blueprint name; it may not contain whitespace or / characters.
    #
    # DEMO http://127.0.0.1:5000/qFLVc2Gt7VTyPL0VLzO0evh5wRF7mK7EQyIOzA7aTapSC1XRHpJyaysv3EhPosLz/coffee
    #
    # GET /secret/name/sha.tar
    # Fetch a source tarball referenced by blueprint name.
    # 
    # Parameters:
    # secret: a 64-byte identifier containing numbers, letters, underscores, and dashes.
    # name: a blueprint name; it may not contain whitespace or / characters.
    # sha: a 40-byte hexadecimal representation of a SHA1 sum.

    with context_managers.mkdtemp():
        r = requests.get(url)

        if r.status_code == 200:
            b = Blueprint(name = urlparse.urlparse(url).path.rpartition('/')[2])
            b.update(json.loads(r.content))

            for filename in b.sources.itervalues():
                r = requests.get(url + '/' + filename)

                if r.status_code == 200:
                    try:
                        tarfile = open(filename, 'w')
                        tarfile.write(r.content)
                    except OSError:
                        return
                    finally:
                        tarfile.close()

                elif r.status_code == 404:
                    logging.error("[404] The sha tarball was not found")
                    return

                elif r.status_code == 502:
                    logging.error("[502] The upstream storage service failed and the blueprint was not pulled")
                    return

                else:
                    logging.error("[%s] GET error retreiving blueprint files" % r.status_code)
                    return

            b.commit('')

        elif r.status_code == 404:
            logging.error("[404] A blueprint could not be pulled from %s" % url)
            return

        else:
            logging.error("[%s] GET error" % r.status_code)
            logging.error(r.history)
            return

    return


def push(b):
    """
    Push a blueprint to server specified in /etc/blueprint-io-server.cfg,
    ~/.blueprint-io.cfg or default to https://devstructure.com
    """

    # GET /secret
    # Create a new secret key known only to the caller. 
	# This is the namespace beneath which the caller’s blueprints are stored.
    
    r = http.get("/secret")

    if r.status == 201:
        secret = r.read().rstrip()
    elif r.status == 502:
        logging.error('[502] GET failure; the upstream storage service failed')
        return
    else:
        logging.error('[%s] GET failure' % r.status)
        return
   
    # PUT /secret/name
    #  Store the JSON representation of the blueprint name. The Content-Type of the body must be application/json.
    # 
    #  Parameters:
    #  secret: a 64-byte identifier containing numbers, letters, underscores, and dashes.
    #  name: a blueprint name; it may not contain whitespace or / characters.
    
    r = http.put(
        url = '/' + secret + '/' + b.name,
        body = b.dumps(),
        headers = {'Content-type': 'application/json'} )

    if r.status == 202:
        logging.info('Your blueprint JSON was stored on server, moving on to the blueprint files')
    elif r.status == 400:
        logging.error('[400] PUT failure; the blueprint was not well-formed')
        return
    elif r.status == 502:
        logging.error('[502] json PUT failure; the upstream storage service failed')
        return
    else:
        logging.error('[%s] json PUT failure' % r.status)
        return
    

    # PUT /secret/name/sha.tar
    # Store a source tarball referenced by blueprint name. The Content-Type of the body must be application/x-tar.
    # 
    # Parameters:
    # secret: a 64-byte identifier containing numbers, letters, underscores, and dashes.
    # name: a blueprint name; it may not contain whitespace or / characters.
    # sha: a 40-byte hexadecimal representation of a SHA1 sum.

    tree = git.tree(b._commit)
    for dirname, filename in sorted(b.sources.iteritems()):
        blob = git.blob(tree, filename)
        content = git.content(blob)
        r = http.put(
            url = '/' + secret + '/' + b.name + '/' + filename,
            body = content,
            headers = {'Content-type': 'application/x-tar'})

    if r.status == 202:
        logging.info('Your blueprint can be retrieved from: %s' % server + '/' + secret + '/' + b.name)
    elif r.status == 400:
        logging.error('[400] tarball PUT failure; the SHA1 sum of the body did not match sha')
    elif r.status == 404:
        logging.error('[404] tarball PUT failure; the secret or blueprint name was not found')
    elif r.status == 502:
        logging.error('[502] tarball PUT failurel the upstream storage service failed')
    else:
        logging.error('[%s] tarball PUT failure' % r.status)
    
    return
    