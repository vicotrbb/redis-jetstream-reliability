// One-off cleanup of the recorded operator-interrupted, synthetic D043 stream.
// Executed only inside the homelab runner after its state was preserved.
package main

import (
    "fmt"
    "time"
    "github.com/nats-io/nats.go"
)

func main() {
    nc, err := nats.Connect("nats://nats-always:4222", nats.Timeout(30*time.Second))
    if err != nil { panic(err) }
    defer nc.Close()
    js, err := nc.JetStream(nats.MaxWait(30*time.Second))
    if err != nil { panic(err) }
    if err = js.DeleteStream("D043"); err != nil { panic(err) }
    fmt.Println("Deleted only preserved operator-interrupted stream D043")
}
