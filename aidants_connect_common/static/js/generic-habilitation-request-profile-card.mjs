import {Controller} from "Stimulus";
import {aidantsConnectApplicationReady, BaseController} from "AidantsConnectApplication";

const MODAL_STATES = Object.freeze({
    IDLE: 1,
    LOADING: 2,
    ERROR: 3,
})

/**
 * @property {HTMLElement} contentTarget
 * @property {HTMLElement} titleTarget
 * @property {HTMLElement} footerTarget
 * @property {HTMLImageElement} loaderTarget
 * @property {HTMLElement} errorTarget
 * @property {HTMLElement[]} footerButtonTargets
 * @property {ProfileEditCard[]} profileEditCardOutlets
 * @property {String} idValue
 * @property {Number} stateValue
 * @property {Boolean} displayValue
 */
class ProfileEditModal extends BaseController {
    static outlets = ["profile-edit-card"]
    static targets = ["title", "content", "footer", "loader", "error", "footerButton"]
    static values = {
        id: {type: String, default: undefined},
        state: {type: Number, default: MODAL_STATES.IDLE},
        display: {type: Boolean, default: false},
    }

    initialize () {
        /** @type {{String: ProfileEditCard}} */
        this.profileEditCards = {}
        this.timeoutId = undefined;
    }

    stateValueChanged (state) {
        this.setContentVisibility(state)
        this.setFooterVisibility(state)
        this.setErrorVisibility(state)
        this.setFooterButtonsVisibility(state)
    }

    displayValueChanged (display) {
        try {  // Prevent stimulus from crashing when DSFR is not ready yet
            if (display) {
                // Prevent the modal content from being erased in the future
                // if we're about to display it
                clearTimeout(this.timeoutId);
                dsfr(this.element).modal.disclose();
            } else {
                dsfr(this.element).modal.conceal();
            }
        } catch {}
    }

    /**@param {ProfileEditCard} outlet  */
    profileEditCardOutletConnected (outlet) {
        this.profileEditCards[outlet.idValue] = outlet
    }

    /**@param {ProfileEditCard} outlet  */
    profileEditCardOutletDisconnected (outlet) {
        delete this.profileEditCards[outlet.idValue]
    }

    /**
     * @param {String} title Modal title
     * @param {String|Promise<String>} content Modal content as HTML string or promise that resolves into HTML string
     * @param {String} id Id of the item being edited
     */
    createAndShow ({title = undefined, content, id} = {}) {
        this.idValue = id
        if (content instanceof Promise) {
            this.stateValue = MODAL_STATES.LOADING;
        } else {
            content = Promise.resolve(content);
        }

        content.then(html => {
            this.contentTarget.innerHTML = html;
            this.idValue = id;
            this.stateValue = MODAL_STATES.IDLE;
        }).catch(() => {
            this.stateValue = MODAL_STATES.ERROR;
        })

        this.displayValue = true
    }

    onValidate (evt) {
        if (this.idValue === undefined || this.stateValue !== MODAL_STATES.IDLE) {
            return
        }

        const controller = this.profileEditCards[this.idValue]
        if (!controller) {
            this.displayValue = false;
            return;
        }

        this.stateValue = MODAL_STATES.LOADING
        controller
            .validate()
            .then(result => {
                // All is well; empty modal and hide
                if (result === undefined) {
                    // Prevent from acting on this record after action success
                    this.idValue = undefined
                    this.displayValue = false
                } else {
                    this.contentTarget.innerHTML = result
                    this.stateValue = MODAL_STATES.IDLE
                }
            })
            .catch(err => {
                console.error(err)
                this.stateValue = MODAL_STATES.ERROR;
            })

    }

    onDelete (evt) {
        if (this.idValue === undefined || this.stateValue !== MODAL_STATES.IDLE) {
            return
        }

        const controller = this.profileEditCards[this.idValue]
        if (!controller) {
            this.displayValue = false;
            return;
        }
        this.stateValue = MODAL_STATES.LOADING
        controller
            .delete()
            .then(() => {
                // All is well; empty modal and hide
                this.idValue = undefined
                this.displayValue = false
            })
            .catch(err => {
                console.error(err)
                this.stateValue = MODAL_STATES.ERROR;
            })
    }

    onConceal (evt) {
        // Reflect changes produced by clicking outside the dialog
        this.displayValue = false
        this.timeoutId = setTimeout(() => {
            // Modify display after modal has disapeared
            this.contentTarget.innerHTML = ""
            this.stateValue = MODAL_STATES.IDLE
        }, 300)
    }

    // region elements visibility
    setContentVisibility (state) {
        if (state === MODAL_STATES.IDLE) {
            this.showElement(this.contentTarget);
        } else {
            this.hideElement(this.contentTarget);
        }
    }

    setFooterVisibility (state) {
        if (state === MODAL_STATES.IDLE) {
            this.showElement(this.footerTarget);
        } else {
            this.hideElement(this.footerTarget);
        }
    }

    setLoaderVisibility (state) {
        if (state === MODAL_STATES.LOADING) {
            this.showElement(this.loaderTarget);
        } else {
            this.hideElement(this.loaderTarget);
        }
    }

    setErrorVisibility (state) {
        if (state === MODAL_STATES.ERROR) {
            this.showElement(this.errorTarget);
        } else {
            this.hideElement(this.errorTarget);
        }
    }

    setFooterButtonsVisibility (state) {
        this.footerButtonTargets.forEach(it => {
            if (state === MODAL_STATES.IDLE) {
                it.removeAttribute("disabled")
            } else {
                it.setAttribute("disabled", "disabled")
            }
        })
    }

    //endregion
}

/**
 * @property {String} idValue
 * @property {String} enpointValue
 * @property {ProfileEditModal} profileEditModalOutlet
 */
class ProfileEditCard extends Controller {
    static values = {id: String, enpoint: String}
    static outlets = ["profile-edit-modal"]

    onEdit (elt) {
        this.profileEditModalOutlet.createAndShow({
            id: this.idValue,
            content: fetch(this.enpointValue).then(async response => {
                if (!response.ok) {
                    throw response.statusText
                }
                return await response.text();
            })
        });
    }

    /** @returns {Promise<String|undefined>} */
    async validate () {
        return fetch(this.enpointValue, {
            body: new FormData(this.profileEditModalOutlet.contentTarget.querySelector("form")),
            method: "POST",
        }).then(async response => {
            // Error in the form, we return the HTML so that modal can display it
            if (response.status === 422) {
                return await response.text()
            }

            // Other error. Modal should display error message
            if (!response.ok) {
                throw response.statusText
            }

            // All is good. Update the <details> and return undefined to let the modal know it shoud close
            this.element.outerHTML = await response.text();
            return undefined
        })
    }

    /** @returns {Promise} */
    async delete () {
        const form = new FormData(this.profileEditModalOutlet.contentTarget.querySelector("form"))
        return fetch(this.enpointValue, {
            method: "DELETE",
            headers: {"X-CSRFToken": form.get("csrfmiddlewaretoken")}
        }).then(async response => {
            if (response.status === 202) {
                this.element.remove();
                return
            }

            throw response.statusText
        })
    }
}

aidantsConnectApplicationReady.then(/** @param {Stimulus.Application} app */ app => app.register("profile-edit-modal", ProfileEditModal))
aidantsConnectApplicationReady.then(/** @param {Stimulus.Application} app */ app => app.register("profile-edit-card", ProfileEditCard))
