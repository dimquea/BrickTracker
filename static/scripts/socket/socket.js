// Socket class
class BrickSocket {
    constructor(id, path, namespace, messages, bulk=false) {
        this.id = id;
        this.path = path;
        this.namespace = namespace;
        this.messages = messages;

        this.disabled = false;
        this.socket = undefined;

        // Bulk mode
        this.bulk = bulk;

        // Form elements (built based on the initial id)
        this.html_complete = document.getElementById(`${id}-complete`);
        this.html_count = document.getElementById(`${id}-count`);
        this.html_fail = document.getElementById(`${id}-fail`);
        this.html_progress = document.getElementById(`${id}-progress`);
        this.html_progress_bar = document.getElementById(`${id}-progress-bar`);
        this.html_progress_message = document.getElementById(`${id}-progress-message`);
        this.html_spinner = document.getElementById(`${id}-spinner`);
        this.html_status = document.getElementById(`${id}-status`);
        this.html_status_icon = document.getElementById(`${id}-status-icon`);

        // Socket status
        window.setInterval(((bricksocket) => () => {
            bricksocket.status();
        })(this), 1000);
    }

    // Clear form
    clear() {
        this.clear_status();

        if (this.html_count) {
            this.html_count.classList.add("d-none");
        }

        if(this.html_progress_bar) {
            this.html_progress.setAttribute("aria-valuenow", "0");
            this.html_progress_bar.setAttribute("style", "width: 0%");
            this.html_progress_bar.textContent = "";
        }

        this.progress_message("");

        this.spinner(false);
    }

    // Clear status message
    clear_status() {
        if (this.html_complete) {
            this.html_complete.classList.add("d-none");

            if (this.bulk) {
                this.html_complete.innerHTML = "";
            } else {
                this.html_complete.textContent = "";
            }
        }

        if (this.html_fail) {
            this.html_fail.classList.add("d-none");
            this.html_fail.textContent = "";
        }
    }

    // Upon receiving a complete message
    complete(data) {
        if(this.html_progress_bar) {
            this.html_progress.setAttribute("aria-valuenow", "100");
            this.html_progress_bar.setAttribute("style", "width: 100%");
            this.html_progress_bar.textContent = "100%";
        }

        if (this.bulk) {
            if (this.html_complete) {
                this.html_complete.classList.remove("d-none");

                // Create a message (not ideal as it is template inside code)
                const success = document.createElement("div");
                success.classList.add("alert", "alert-success");
                success.setAttribute("role", "alert");
                success.innerHTML = `<strong>Success:</strong> ${data.message}`

                this.html_complete.append(success)
            }
        } else {
            this.spinner(false);

            if (this.html_complete) {
                this.html_complete.classList.remove("d-none");
                this.html_complete.innerHTML = `<strong>Success:</strong> ${data.message}`;
            }

            if (this.html_fail) {
                this.html_fail.classList.add("d-none");
            }
        }
    }

    // Update the count
    count(count, total) {
        if (this.html_count) {
            this.html_count.classList.remove("d-none");

            // If there is no total, display a question mark instead
            if (total == 0) {
                total = "?"
            }

            this.html_count.textContent = `(${count}/${total})`;
        }
    }

    // Upon receiving a fail message
    fail(data) {
        this.spinner(false);

        if (this.html_fail) {
            this.html_fail.classList.remove("d-none", );
            this.html_fail.innerHTML = `<strong>Error:</strong> ${data.message}`;
        }

        if (!this.bulk && this.html_complete) {
            this.html_complete.classList.add("d-none");
        }

        if (this.html_progress_bar) {
            this.html_progress_bar.classList.remove("progress-bar-animated");
        }
    }


    // Update the progress
    progress(data={}) {
        let total = data["total"];
        let count = data["count"]

        // Fix the total if bogus
        if (!total || isNaN(total) || total <= 0) {
            total = 0;
        }

        // Fix the count if bogus
        if (!count || isNaN(count) || count <= 1) {
            count = 1;
        }

        this.count(count, total);
        this.progress_message(data["message"]);

        if (this.html_progress && this.html_progress_bar) {
            // Infinite progress bar
            if (!total) {
                this.html_progress.setAttribute("aria-valuenow", "100");
                this.html_progress_bar.classList.add("progress-bar-striped", "progress-bar-animated");
                this.html_progress_bar.setAttribute("style", "width: 100%");
                this.html_progress_bar.textContent = "";
            } else {
                if (count > total) {
                    total = count;
                }

                const progress = (count - 1) * 100 / total;

                this.html_progress.setAttribute("aria-valuenow", progress);
                this.html_progress_bar.classList.remove("progress-bar-striped", "progress-bar-animated");
                this.html_progress_bar.setAttribute("style", `width: ${progress}%`);
                this.html_progress_bar.textContent = `${progress.toFixed(2)}%`;
            }
        }
    }

    // Update the progress message
    progress_message(message) {
        if (this.html_progress_message) {
            this.html_progress_message.classList.remove("d-none");
            this.html_progress_message.textContent = message;
        }
    }

    // Setup the actual socket
    setup() {
        if (this.socket === undefined) {
            this.socket = io.connect(`${window.location.origin}/${this.namespace}`, {
                // Local patch: behind a path-prefixing proxy the origin
                // alone does not reach the application. Every socket goes
                // through here, so this is the only place that needs it.
                path: `${window.BK_ROOT || ""}${this.path}`,
                // Adding Polling as iOS is having issues with websockets
                transports: ["polling", "websocket"],
                // Increase timeout for slow mobile connections
                timeout: 30000,
                // Reconnection settings
                reconnectionDelay: 1000,
                reconnectionDelayMax: 5000,
                // Allow upgrade from polling to websocket
                upgrade: true,
            });

            // Complete
            this.socket.on(this.messages.COMPLETE, ((bricksocket) => (data) => {
                bricksocket.complete(data);
                if (!bricksocket.bulk) {
                    bricksocket.toggle(true);
                }
            })(this));

            // Fail
            this.socket.on(this.messages.FAIL, ((bricksocket) => (data) => {
                bricksocket.fail(data);
                bricksocket.toggle(true);
            })(this));

            // Progress
            this.socket.on(this.messages.PROGRESS, ((bricksocket) => (data) => {
                bricksocket.progress(data);
            })(this));
        }
    }

    // Toggle the spinner
    spinner(show) {
        if (this.html_spinner) {
            if (show) {
                this.html_spinner.classList.remove("d-none");
            } else {
                this.html_spinner.classList.add("d-none");
            }
        }
    }

    // Toggle the status
    status() {
        if (this.html_status) {
            if (this.socket === undefined) {
                this.html_status.textContent = "Socket is not initialized";
                if (this.html_status_icon) {
                    this.html_status_icon.classList.remove("ri-checkbox-circle-fill", "ri-close-circle-fill");
                    this.html_status_icon.classList.add("ri-question-fill");
                }
            } else if (this.socket.connected) {
                this.html_status.textContent = "Socket is connected";
                if (this.html_status_icon) {
                    this.html_status_icon.classList.remove("ri-question-fill", "ri-close-circle-fill");
                    this.html_status_icon.classList.add("ri-checkbox-circle-fill");
                }
            } else {
                this.html_status.textContent = "Socket is disconnected";
                if (this.html_status_icon) {
                    this.html_status_icon.classList.remove("ri-question-fill", "ri-checkbox-circle-fill");
                    this.html_status_icon.classList.add("ri-close-circle-fill");
                }
            }
        }
    }

    // Toggle clicking on the button, or sending events
    toggle(enabled) {
        this.disabled = !enabled;
    }
}
