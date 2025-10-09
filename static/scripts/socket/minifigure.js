// Minifigure Socket class
class BrickMinifigureSocket extends BrickSocket {
    constructor(id, path, namespace, messages) {
        super(id, path, namespace, messages, false);

        // Listeners
        this.add_listener = undefined;
        this.input_listener = undefined;
        this.confirm_listener = undefined;

        // Form elements (built based on the initial id)
        this.html_button = document.getElementById(id);
        this.html_input = document.getElementById(`${id}-set`);
        this.html_no_confim = document.getElementById(`${id}-no-confirm`);
        this.html_owners = document.getElementById(`${id}-owners`);
        this.html_purchase_location = document.getElementById(`${id}-purchase-location`);
        this.html_storage = document.getElementById(`${id}-storage`);
        this.html_tags = document.getElementById(`${id}-tags`);

        // Card elements
        this.html_card = document.getElementById(`${id}-card`);
        this.html_card_set = document.getElementById(`${id}-card-set`);
        this.html_card_name = document.getElementById(`${id}-card-name`);
        this.html_card_image_container = document.getElementById(`${id}-card-image-container`);
        this.html_card_image = document.getElementById(`${id}-card-image`);
        this.html_card_footer = document.getElementById(`${id}-card-footer`);
        this.html_card_confirm = document.getElementById(`${id}-card-confirm`);
        this.html_card_dismiss = document.getElementById(`${id}-card-dismiss`);

        if (this.html_button) {
            this.add_listener = this.html_button.addEventListener("click", ((bricksocket) => (e) => {
                bricksocket.execute();
            })(this));

            this.input_listener = this.html_input.addEventListener("keyup", ((bricksocket) => (e) => {
                if (e.key === 'Enter') {
                    bricksocket.execute();
                }
            })(this))
        }

        if (this.html_card_dismiss && this.html_card) {
            this.html_card_dismiss.addEventListener("click", ((card) => (e) => {
                card.classList.add("d-none");
            })(this.html_card));
        }

        // Setup the socket
        this.setup();
    }

    // Clear form
    clear() {
        super.clear();

        if (this.html_card) {
            this.html_card.classList.add("d-none");
        }

        if (this.html_card_footer) {
            this.html_card_footer.classList.add("d-none");

            if (this.html_card_confirm) {
                this.html_card_footer.classList.add("d-none");
            }
        }
    }

    // Execute the action
    execute() {
        if (!this.disabled && this.socket !== undefined && this.socket.connected) {
            this.toggle(false);

            if (this.html_no_confim && this.html_no_confim.checked) {
                this.import_minifigure(true);
            } else {
                this.load_minifigure();
            }
        }
    }

    // Import a minifigure
    import_minifigure(no_confirm, figure) {
        if (this.html_input) {
            if (no_confirm) {
                this.clear();
            } else {
                this.clear_status();
            }

            // Grab the owners
            const owners = [];
            if (this.html_owners) {
                this.html_owners.querySelectorAll('input').forEach(input => {
                    if (input.checked) {
                        owners.push(input.value);
                    }
                });
            }

            // Grab the purchase location
            let purchase_location = null;
            if (this.html_purchase_location) {
                purchase_location = this.html_purchase_location.value;
            }

            // Grab the storage
            let storage = null;
            if (this.html_storage) {
                storage = this.html_storage.value;
            }

            // Grab the tags
            const tags = [];
            if (this.html_tags) {
                this.html_tags.querySelectorAll('input').forEach(input => {
                    if (input.checked) {
                        tags.push(input.value);
                    }
                });
            }

            this.spinner(true);

            if (this.html_progress_bar) {
                this.html_progress_bar.scrollIntoView();
            }

            this.socket.emit(this.messages.IMPORT_MINIFIGURE, {
                figure: (figure !== undefined) ? figure : this.html_input.value,
                owners: owners,
                purchase_location: purchase_location,
                storage: storage,
                tags: tags,
                quantity: 1
            });
        } else {
            this.fail("Could not find the input field for the minifigure number");
        }
    }

    // Load a minifigure
    load_minifigure() {
        if (this.html_input) {
            // Reset the progress
            this.clear()
            this.spinner(true);

            this.socket.emit(this.messages.LOAD_MINIFIGURE, {
                figure: this.html_input.value
            });
        } else {
            this.fail("Could not find the input field for the minifigure number");
        }
    }

    // Minifigure is loaded
    minifigure_loaded(data) {
        if (this.html_card) {
            this.html_card.classList.remove("d-none");

            if (this.html_card_set) {
                this.html_card_set.textContent = data["figure"];
            }

            if (this.html_card_name) {
                this.html_card_name.textContent = data["name"];
            }

            if (this.html_card_image_container) {
                this.html_card_image_container.setAttribute("style", `background-image: url(${data["image"]})`);
            }

            if (this.html_card_image) {
                this.html_card_image.setAttribute("src", data["image"]);
                this.html_card_image.setAttribute("alt", data["figure"]);
            }

            if (this.html_card_footer) {
                this.html_card_footer.classList.add("d-none");

                if (!data.download) {
                    this.html_card_footer.classList.remove("d-none");

                    if (this.html_card_confirm) {
                        if (this.confirm_listener !== undefined) {
                            this.html_card_confirm.removeEventListener("click", this.confirm_listener);
                        }

                        this.confirm_listener = ((bricksocket, figure) => (e) => {
                            if (!bricksocket.disabled) {
                                bricksocket.toggle(false);
                                bricksocket.import_minifigure(false, figure);
                            }
                        })(this, data["figure"]);

                        this.html_card_confirm.addEventListener("click", this.confirm_listener);

                        this.html_card_confirm.scrollIntoView();
                    }
                }
            }
        }
    }

    // Setup the actual socket
    setup() {
        super.setup();

        if (this.socket !== undefined) {
            // Minifigure loaded
            this.socket.on(this.messages.MINIFIGURE_LOADED, ((bricksocket) => (data) => {
                bricksocket.minifigure_loaded(data);
            })(this));
        }
    }

    // Toggle clicking on the button, or sending events
    toggle(enabled) {
        super.toggle(enabled);

        if (this.html_button) {
            this.html_button.disabled = !enabled;
        }

        if (this.html_input) {
            this.html_input.disabled = !enabled;
        }

        if (this.html_no_confim) {
            this.html_no_confim.disabled = !enabled;
        }

        if (this.html_owners) {
            this.html_owners.querySelectorAll('input').forEach(input => input.disabled = !enabled);
        }

        if (this.html_purchase_location) {
            this.html_purchase_location.disabled = !enabled;
        }

        if (this.html_storage) {
            this.html_storage.disabled = !enabled;
        }

        if (this.html_tags) {
            this.html_tags.querySelectorAll('input').forEach(input => input.disabled = !enabled);
        }

        if (this.html_card_confirm) {
            this.html_card_confirm.disabled = !enabled;
        }

        if (this.html_card_dismiss) {
            this.html_card_dismiss.disabled = !enabled;
        }
    }
}
