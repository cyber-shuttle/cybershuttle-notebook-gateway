// @author: Yasith Jayawardana <yasith@cs.odu.edu>

/*
===================================
Kernel Agent - Cybershuttle Project
===================================

Jupyter Kernel wrapper that eagerly announces itself to Cybershuttle.

Description:
Normally, Jupyter kernels are spawned as "servers" on TCP/ZMQ ports.
Instead, this program spawns them as "clients" to an arbitrary command source.

Key Features:
- Delegate notebook client handling to elsewhere, and just run commands.
- Run commands sent over arbitrary transports (e.g. websocket, message queues).
- Enable external programs to use kernels on-demand.
- Enable external programs to sync state across kernels.

*/

package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"syscall"
	"time"

	"github.com/pebbe/zmq4"
)

type CLIArgs struct {
	conn_file   string
	issuer_addr string
	transport   string
}

type ConnectionInfo struct {
	ShellPort   int64  `json:"shell_port"`
	IopubPort   int64  `json:"iopub_port"`
	StdinPort   int64  `json:"stdin_port"`
	HbPort      int64  `json:"hb_port"`
	ControlPort int64  `json:"control_port"`
	Ip          string `json:"ip"`
	Transport   string `json:"transport"`
}

var (
	SHELL_ID   = "shell"
	IOPUB_ID   = "iopub"
	STDIN_ID   = "stdin"
	HB_ID      = "hb"
	CONTROL_ID = "control"
)

func main() {

	// Setup the graceful termination handler
	var c = create_signal_channel()

	// fallback error handler
	defer func() {
		if err := recover(); err != nil {
			fmt.Println("a critical error occured:", err)
			os.Exit(1)
		}
	}()

	var (
		// read command line args
		args = read_cli_args()
		// Read connection file and validate it
		cf = read_connection_file(args.conn_file)
		// define command to start ipython kernel
		cmd = exec.Command("ipython", "kernel", "-f", args.conn_file)
	)

	// start kernel
	if err := cmd.Start(); err != nil {
		panic(fmt.Errorf("failed to start cmd: %v", err))
	}
	fmt.Printf("started kernel with process id: %v\n", cmd.Process.Pid)
	defer cmd.Process.Kill()
	time.Sleep(500 * time.Millisecond)

	// ROUTER sockets (via REQ)
	var (
		control_addr = fmt.Sprintf("%s://%s:%d", cf.Transport, cf.Ip, cf.ControlPort)
		shell_addr   = fmt.Sprintf("%s://%s:%d", cf.Transport, cf.Ip, cf.ShellPort)
		stdin_addr   = fmt.Sprintf("%s://%s:%d", cf.Transport, cf.Ip, cf.StdinPort)
		hb_addr      = fmt.Sprintf("%s://%s:%d", cf.Transport, cf.Ip, cf.HbPort)
		iopub_addr   = fmt.Sprintf("%s://%s:%d", cf.Transport, cf.Ip, cf.IopubPort)
		issuer_addr  = fmt.Sprintf("%s://%s", args.transport, args.issuer_addr)
	)

	// connect issuer <-> ports
	fmt.Println("use Ctrl+C to shutdown the service")
	start_tunneling(issuer_addr, control_addr, shell_addr, stdin_addr, hb_addr, iopub_addr)
	<-c
	fmt.Println("shutting down...")
}

// read command-line arguments to get connection parameters and
func read_cli_args() CLIArgs {
	p_conn_file := flag.String("conn_file", "", "Filepath to get kernel connection info from")
	p_issuer_addr := flag.String("issuer_addr", "", "URL of command issuer")
	p_transport := flag.String("transport", "", "Name of transport protocol")
	flag.Parse()
	args := CLIArgs{*p_conn_file, *p_issuer_addr, *p_transport}
	// validation
	if len(args.conn_file) == 0 {
		panic(fmt.Errorf("conn_file must be defined"))
	}
	if len(args.issuer_addr) == 0 {
		panic(fmt.Errorf("issuer_addr must be defined"))
	}
	if len(args.transport) == 0 {
		panic(fmt.Errorf("transport must be defined"))
	}
	return args
}

func read_connection_file(path string) ConnectionInfo {
	var conn ConnectionInfo
	data, err := os.ReadFile(path)
	if err != nil {
		panic(fmt.Errorf("error when opening JSON: %v", err))
	}
	err = json.Unmarshal(data, &conn)
	if err != nil {
		panic(fmt.Errorf("error when parsing JSON data: %v", err))
	}
	fmt.Printf("%v\n", conn)
	return conn
}

// tunnel data -> issuer
func start_tunneling(
	issuer_addr string,
	control_addr string,
	shell_addr string,
	stdin_addr string,
	hb_addr string,
	iopub_addr string,
) {
	// Create a new context
	context, _ := zmq4.NewContext()
	defer context.Term()

	connect := func(addr string, typ zmq4.Type) *zmq4.Socket {
		sock, err := context.NewSocket(typ)
		if err != nil {
			panic(fmt.Errorf("failed to setup ZMQ socket: %v", err))
		}
		err = sock.Connect(addr)
		if err != nil {
			panic(fmt.Errorf("failed to connect to ZMQ socket: %v", err))
		}
		fmt.Printf("connected to ZMQ socket: %s\n", addr)
		return sock
	}

	// control (ROUTER host)
	control := connect(control_addr, zmq4.REQ)
	defer control.Close()

	// shell (ROUTER host)
	shell := connect(shell_addr, zmq4.REQ)
	defer shell.Close()

	// stdin (ROUTER host)
	stdin := connect(stdin_addr, zmq4.REQ)
	defer stdin.Close()

	// hb (REP host)
	hb := connect(hb_addr, zmq4.REQ)
	defer hb.Close()

	// iopub (PUB host)
	iopub := connect(iopub_addr, zmq4.SUB)
	defer iopub.Close()

	// issuer (ROUTER host)
	issuer := connect(issuer_addr, zmq4.DEALER)
	defer issuer.Close()

	// define mux and demux functions
	mux := func(dest *zmq4.Socket, src *zmq4.Socket, name string, header [][]byte) {
		for {
			parts, err := src.RecvMessageBytes(0)
			if err != nil {
				panic(fmt.Errorf("error reading '%s' message: %v", name, err))
			}
			total, err := dest.SendMessage(append(header, parts...))
			if err != nil {
				panic(fmt.Errorf("error sending '%s' message: %v", name, err))
			}
			fmt.Printf("%d bytes sent over '%s'\n", total, name)
		}
	}
	demux := func() {
		for {
			parts, err := issuer.RecvMessageBytes(0)
			if err != nil {
				panic(fmt.Errorf("error reading 'issuer' message: %v", err))
			}
			switch string(parts[0]) {
			case SHELL_ID:
				shell.SendMessage(parts[1:])
			case IOPUB_ID:
				iopub.SendMessage(parts[1:])
			case STDIN_ID:
				stdin.SendMessage(parts[1:])
			case HB_ID:
				hb.SendMessage(parts[1:])
			case CONTROL_ID:
				control.SendMessage(parts[1:])
			default:
				panic(fmt.Errorf("unsupported message format: %v", err))
			}
		}
	}

	// define prefixes for muxing/demuxing
	var (
		control_hdr = [][]byte{[]byte(CONTROL_ID)}
		shell_hdr   = [][]byte{[]byte(SHELL_ID)}
		stdin_hdr   = [][]byte{[]byte(STDIN_ID)}
		iopub_hdr   = [][]byte{[]byte(IOPUB_ID)}
		hb_hdr      = [][]byte{[]byte(HB_ID)}
	)

	// start muxing (* -> issuer) and demuxing (issuer -> *)
	go mux(issuer, control, "control", control_hdr)
	go mux(issuer, shell, "shell", shell_hdr)
	go mux(issuer, stdin, "stdin", stdin_hdr)
	go mux(issuer, iopub, "iopub", iopub_hdr)
	go mux(issuer, hb, "hb", hb_hdr)
	demux()
	fmt.Println("end of start_tunneling()")

}

// perform a graceful shutdown
func create_signal_channel() chan os.Signal {
	c := make(chan os.Signal, 1)
	signal.Notify(c, syscall.SIGTERM, os.Interrupt)
	return c
}
