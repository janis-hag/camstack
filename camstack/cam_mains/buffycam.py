# Quick shorthand for testing
from camstack.core.utilities import DependentProcess, RemoteDependentProcess
from camstack.cams.cred1 import Buffy

import scxconf

if __name__ == "__main__":

    mode = 0

    # Prepare dependent processes
    tcp_recv = RemoteDependentProcess(
        tmux_name=f'streamTCPreceive_{scxconf.BUFFY_PORT}',
        # Urrrrrh this is getting messy
        cli_cmd='creashmim %s %u %u; shmimTCPreceive -c ircam ' +
        f'{scxconf.BUFFY_PORT}',
        cli_args=('kcam', 320, 256),
        remote_host=scxconf.IP_SC6_LAN,
        kill_upon_create=False,
    )
    tcp_recv.start_order = 1
    tcp_recv.kill_order = 1

    tcp_send = DependentProcess(
        tmux_name='kcam_tcp',
        cli_cmd=
        'sleep 3; OMP_NUM_THREADS=1 /home/scexao-op/bin/shmimTCPtransmit-simple %s %s %u',
        cli_args=('kcam', scxconf.IP_SC6_P2P70, scxconf.BUFFY_PORT),
        # Sender is kill_upon_create - rather than when starting. that ensures it dies well before the receiver
        # Which is better for flushing TCP sockets
        kill_upon_create=True,
        cset='buffy_tcp',
        rtprio=49,
    )
    tcp_send.start_order = 2
    tcp_send.kill_order = 0

    # TODO register those 2 to the "Buffy" object and make csets for them ?
    # Prepare dependent processes
    tcp_recv_raw = RemoteDependentProcess(
        tmux_name=f'streamTCPreceive_{scxconf.BUFFY_PORT_RAW}',
        # Urrrrrh this is getting messy
        cli_cmd=
        'milk-exec "creaushortimshm %s %u %u"; shmimTCPreceive -c ircam ' +
        f'{scxconf.BUFFY_PORT_RAW}',
        cli_args=('kcam_raw', 320, 256),
        remote_host=scxconf.IP_SC6_LAN,
        kill_upon_create=False,
    )
    tcp_recv.start_order = 3
    tcp_recv.kill_order = 4

    tcp_send_raw = DependentProcess(
        tmux_name='kcam_raw_tcp',
        cli_cmd=
        'sleep 3; OMP_NUM_THREADS=1 /home/scexao-op/bin/shmimTCPtransmit-simple %s %s %u',
        cli_args=('kcam_raw', scxconf.IP_SC6_P2P70, scxconf.BUFFY_PORT_RAW),
        # Sender is kill_upon_create - rather than when starting. that ensures it dies well before the receiver
        # Which is better for flushing TCP sockets
        kill_upon_create=True,
        cset='buffy_tcp',
        rtprio=48,
    )
    tcp_send.start_order = 4
    tcp_send.kill_order = 3

    utr_red = DependentProcess(
        tmux_name='kcam_utr',
        cli_cmd=
        'milk-exec "mload milkimageformat; readshmim kcam_raw; imgformat.cred_ql_utr ..procinfo 1; imgformat.cred_ql_utr ..triggermode 3; imgformat.cred_ql_utr ..loopcntMax -1; imgformat.cred_ql_utr kcam_raw kcam 55000"',
        cli_args=(),
        kill_upon_create=True,
        cset='buffy_utr',
        rtprio=49,
    )
    utr_red.start_order = 0
    utr_red.kill_order = 2

    cam = Buffy('kcam',
                'kcam_raw',
                unit=1,
                channel=0,
                mode_id='full',
                taker_cset_prio=('buffy_edt', 49),
                dependent_processes=[tcp_recv, tcp_send,
                                     utr_red])  #, tcp_send_raw, tcp_recv_raw])

    from camstack.core.utilities import shellify_methods
    shellify_methods(cam, globals())
s