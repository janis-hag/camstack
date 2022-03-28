# Quick shorthand for testing
from camstack.core.utilities import DependentProcess, RemoteDependentProcess
from camstack.cams.cred2 import GLINT

import os
import scxconf

if __name__ == "__main__":

    mode = 13 #12

    # Prepare dependent processes
    tcp_recv = RemoteDependentProcess(
        tmux_name=f'streamTCPreceive_{scxconf.TCPPORT_GLINT}',
        # Urrrrrh this is getting messy
        cli_cmd=
        'milk-exec "creasshortimshm %s %u %u"; shmimTCPreceive -c ircam ' +
        f'{scxconf.TCPPORT_GLINT}',
        cli_args=('glint', 320, 256),
        remote_host=scxconf.IP_SC6,
        kill_upon_create=False,
    )
    tcp_recv.start_order = 0
    tcp_recv.kill_order = 1

    tcp_send = DependentProcess(
        tmux_name='glint_tcp',
        cli_cmd=
        'sleep 3; OMP_NUM_THREADS=1 shmimTCPtransmit %s %s %u',
        cli_args=('glint', scxconf.IPP2P_SC6FROM5, scxconf.TCPPORT_GLINT),
        # Sender is kill_upon_create - rather than when starting. that ensures it dies well before the receiver
        # Which is better for flushing TCP sockets
        kill_upon_create=True,
        cset='glint_tcp',
        rtprio=40,
    )
    tcp_send.start_order = 1
    tcp_send.kill_order = 0
    
    try:
        os.makedirs(os.environ['MILK_SHM_DIR'] + '/smb')  # Samba server root
    except FileExistsError:
        pass

    fits_dump = DependentProcess(
        tmux_name='glint_fits',
        cli_cmd='OMP_NUM_THREADS=1 shmim2rollingFits %s %s %f glint_fits',
        cli_args=('glint', os.environ['MILK_SHM_DIR'] + "/smb/", 0.03),
        kill_upon_create=False,
    )
    fits_dump.start_order = 2
    fits_dump.kill_order = 2

    # PIPE over ZMQ into the LAN until we find a better solution (receiver)
    zmq_recv = RemoteDependentProcess(
        tmux_name='glint_zmq',
        cli_cmd='zmq_recv.py %s:%u %s',
        cli_args=(scxconf.IPLAN_SC5, scxconf.ZMQPORT_GLINT, 'glint'),
        remote_host=f'scexao-op@{scxconf.IP_SC2}',
        kill_upon_create=False,
    )
    zmq_recv.start_order = 3
    zmq_recv.kill_order = 4

    # PIPE over ZMQ into the LAN until we find a better solution (sender)
    zmq_send = DependentProcess(
        tmux_name='glint_zmq',
        cli_cmd='zmq_send.py %s:%u %s -f 100',
        cli_args=(scxconf.IPLAN_SC5, scxconf.ZMQPORT_GLINT, 'glint'),
        kill_upon_create=True,
    )
    zmq_send.start_order = 4
    zmq_send.kill_order = 3


    cam = GLINT('glint',
                'glint',
                unit=5,
                channel=0,
                mode_id=mode,
                taker_cset_prio=('glint_edt', 41),
                dependent_processes=[tcp_recv, tcp_send, fits_dump, zmq_recv, zmq_send])

    from camstack.core.utilities import shellify_methods
    shellify_methods(cam, globals())
