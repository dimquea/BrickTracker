// Set Socket class
class BrickSetSocket extends BrickSocket {
    constructor(id, path, namespace, messages, bulk=false, refresh=false) {
        super(id, path, namespace, messages, bulk);

        // Refresh mode
        this.refresh = refresh

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

    // Upon receiving a complete message
    complete(data) {
        super.complete(data);

        if (this.bulk) {
            // Import the next set
            this.import_set(true, undefined, true);
        }
    }

    // Execute the action
    execute() {
        if (!this.disabled && this.socket !== undefined && this.socket.connected) {
            this.toggle(false);

            // Split and save the list if bulk
            if (this.bulk) {
                this.read_set_list();
            }

            if (this.bulk || this.refresh || (this.html_no_confim && this.html_no_confim.checked)) {
                this.import_set(true);
            } else {
                this.load_set();
            }
        }
    }

    // Upon receiving a fail message
    fail(data) {
        super.fail(data);

        if (this.bulk && this.html_input) {
            if (this.set_list_last_set !== undefined) {
                this.set_list.unshift(this.set_list_last_set);
                this.set_list_last_set = undefined;
            }

            this.html_input.value = this.set_list.join(', ');
        }
    }

    // Import a set
    import_set(no_confirm, set, from_complete=false) {
        if (this.html_input) {
            if (!this.bulk || !from_complete) {
                // Reset the progress
                if (no_confirm) {
                    this.clear();
                } else {
                    this.clear_status();
                }
            }

            // Grab from the list if bulk
            if (this.bulk) {
                set = this.set_list.shift()

                // Abort if nothing left to process
                if (set === undefined) {
                    // Clear the input
                    this.html_input.value = "";

                    // Settle the form
                    this.spinner(false);
                    this.toggle(true);

                    return;
                }

                // Save the pulled set
                this.set_list_last_set = set;
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

            // Determine if this is a set or minifigure
            const itemValue = (set !== undefined) ? set : this.html_input.value;
            const isMinifigure = itemValue.trim().startsWith('fig-') || itemValue.trim().match(/^fig\d/i);

            if (isMinifigure) {
                // Emit minifigure import message
                this.socket.emit(this.messages.IMPORT_MINIFIGURE, {
                    figure: itemValue,
                    owners: owners,
                    purchase_location: purchase_location,
                    storage: storage,
                    tags: tags,
                    quantity: 1
                });
            } else {
                // Emit set import message
                this.socket.emit(this.messages.IMPORT_SET, {
                    set: itemValue,
                    owners: owners,
                    purchase_location: purchase_location,
                    storage: storage,
                    tags: tags,
                    refresh: this.refresh
                });
            }
        } else {
            this.fail("Could not find the input field for the set number");
        }
    }

    // Load a set
    load_set() {
        if (this.html_input) {
            // Reset the progress
            this.clear()
            this.spinner(true);

            this.socket.emit(this.messages.LOAD_SET, {
                set: this.html_input.value
            });
        } else {
            this.fail("Could not find the input field for the set number");
        }
    }

    // Bulk: read the input as a list
    read_set_list() {
        this.set_list = [];

        if (this.html_input) {
            const value = this.html_input.value;
            this.set_list = value.split(",").map((el) => el.trim())
        }
    }

    // Set is loaded
    set_loaded(data) {
        if (this.html_card) {
            this.html_card.classList.remove("d-none");

            if (this.html_card_set) {
                this.html_card_set.textContent = data["set"];
            }

            if (this.html_card_name) {
                this.html_card_name.textContent = data["name"];
            }

            if (this.html_card_image_container) {
                this.html_card_image_container.setAttribute("style", `background-image: url(${data["image"]})`);
            }

            if (this.html_card_image) {
                this.html_card_image.setAttribute("src", data["image"]);
                this.html_card_image.setAttribute("alt", data["set"]);
            }

            if (this.html_card_footer) {
                this.html_card_footer.classList.add("d-none");

                if (!data.download) {
                    this.html_card_footer.classList.remove("d-none");

                    if (this.html_card_confirm) {
                        if (this.confirm_listener !== undefined) {
                            this.html_card_confirm.removeEventListener("click", this.confirm_listener);
                        }

                        this.confirm_listener = ((bricksocket, set) => (e) => {
                            if (!bricksocket.disabled) {
                                bricksocket.toggle(false);
                                bricksocket.import_set(false, set);
                            }
                        })(this, data["set"]);

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
            // Set loaded
            this.socket.on(this.messages.SET_LOADED, ((bricksocket) => (data) => {
                bricksocket.set_loaded(data);
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

        if (!this.bulk && this.html_no_confim) {
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
