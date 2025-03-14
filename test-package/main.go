package main

import (
	"log"
	"net/http"
)

func Handler(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("Hello, world\n"))
}

func main() {
	http.HandleFunc("/", Handler)

	log.Println("Starting HTTP server on :1234")
	log.Fatal(http.ListenAndServe(":1234", nil))
}
