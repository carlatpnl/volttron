import tempfile

import gevent
import os
import pytest
import requests

from volttron.platform.keystore import KeyStore
from volttron.platform.vip.agent import Agent


def validate_instances(wrapper1, wrapper2):
    assert wrapper1.bind_web_address
    assert wrapper2.bind_web_address
    assert wrapper1.bind_web_address != wrapper2.bind_web_address
    assert wrapper1.volttron_home
    assert wrapper2.volttron_home
    assert wrapper1.volttron_home != wrapper2.volttron_home

@pytest.mark.vc
def test_discovery(vc_instance, pa_instance):
    vc_wrapper = vc_instance['wrapper']
    pa_wrapper = pa_instance['wrapper']

    paurl = "http://{}/discovery/".format(pa_wrapper.bind_web_address)
    vcurl = "http://{}/discovery/".format(vc_wrapper.bind_web_address)

    pares = requests.get(paurl)
    assert pares.ok
    data = pares.json()
    assert data['serverkey']
    assert data['vip-address']

    vcres = requests.get(vcurl)
    assert vcres.ok
    data = vcres.json()
    assert data['serverkey']
    assert data['vip-address']

@pytest.mark.vc
def test_register_instance(vc_instance, pa_instance):
    vc_wrapper = vc_instance['wrapper']
    pa_wrapper = pa_instance['wrapper']

    validate_instances(vc_wrapper, pa_wrapper)

    print("connecting to vc instance with vip_adddress: {}".format(
        pa_wrapper.vip_address)
    )

    authfile = os.path.join(vc_wrapper.volttron_home, "auth.json")
    with open(authfile) as f:
        print("vc authfile: {}".format(f.read()))

    tf = tempfile.NamedTemporaryFile()
    paks = KeyStore(tf.name)
    paks.generate()  #needed because using a temp file!!!!
    print('Checking peers on pa using:\nserverkey: {}\npublickey: {}\n'
          'secretkey: {}'.format(
        pa_wrapper.publickey,
        paks.public(),
        paks.secret()
    ))
    paagent = pa_wrapper.build_agent(serverkey=pa_wrapper.publickey,
                                     publickey=paks.public(),
                                     secretkey=paks.secret())
    peers = paagent.vip.peerlist().get(timeout=3)
    assert "platform.agent" in peers
    paagent.core.stop()
    del paagent

    tf = tempfile.NamedTemporaryFile()
    ks = KeyStore(tf.name)
    ks.generate()  #needed because using a temp file!!!!!
    print('Checking peers on vc using:\nserverkey: {}\npublickey: {}\n'
          'secretkey: {}'.format(
        vc_wrapper.publickey,
        ks.public(),
        ks.secret()
    ))

    # Create an agent to use for calling rpc methods on volttron.central.
    controlagent = vc_wrapper.build_agent(serverkey=vc_wrapper.publickey,
                                          publickey=ks.public(),
                                          secretkey=ks.secret())
    plist = controlagent.vip.peerlist().get(timeout=2)
    assert "volttron.central" in plist

    print('Attempting to manage platform now.')
    retval = controlagent.vip.rpc.call("volttron.central", "register_instance",
                                        uri=pa_wrapper.bind_web_address,
                                        display_name="hushpuppy").get(timeout=10)

    assert retval
    assert 'hushpuppy' == retval['display_name']
    assert retval['success']
    controlagent.core.stop()

    # # build agent to interact with the vc agent on the vc_wrapper instance.
    # #agent = vc_wrapper.build_agent(**params)
    # # serverkey=vc_wrapper.publickey,
    # #                                publickey=ks.public(),
    # #                                secretkey=ks.secret())
    # with open(authfile) as f:
    #     print("vc authfile: {}".format(f.read()))
    # peers = agent.vip.peerlist().get(timeout=2)
    # assert "volttron.central" in peers

