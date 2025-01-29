import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

const STATES = Object.freeze({
    IDLE: "IDLE",
    LOADING: "LOADING",
})

/**
 * @property {HTMLFormElement} formTarget
 * @property {HTMLInputElement} TOTAL_FORMSTarget
 * @property {HTMLElement} leftFormReplaceTarget
 * @property {HTMLElement[]} submitBtnTargets
 * @property {HTMLElement} rightFormsInsertContainerTarget
 * @property {HTMLElement} rightFormsInsertTarget
 * @property {HTMLElement} formTplTarget
 *
 * @property {String} stateValue
 * @property {String} actionUrlValue
 */
class NewHabilitationRequest extends BaseController {
    static targets = [
        "TOTAL_FORMS",
        "leftFormReplace",
        "submitBtn",
        "rightFormsInsertContainer",
        "rightFormsInsert",
        "formTpl",
        "confirmationDialog",
        "dialogConfirmButton",
        "dialogCancelButton",
    ]
    static values = {
        state: {type: String, default: STATES.IDLE},
        nbFormCount: {type: Number, default: -1},
        modalOpened: {type: Boolean, default: false},
        actionUrl: {type: String},
    }
    static classes = ["loading", "submitBtnEdit", "submitBtnValidate"]
    static outlets = ["profile-edit-card"]

    initialize () {
        this.nbFormCountValue = Number.parseInt(this.TOTAL_FORMSTarget.value)
        if (this.leftFormReplaceTarget.children.length === 0) {
            // If formset is not valid, it should already be displaying the last invalid form
            this.validateAndResetLeftForm()
        }
        this.formTarget = this.element.closest("form")
    }

    profileEditCardOutletConnected (outlet) {
        outlet.additionnalData = this.additionnalData.bind(this)
    }

    additionnalData () {
        return `${new URLSearchParams(new FormData(this.formTarget))}`
    }

    nbFormCountValueChanged (value) {
        if (this.stateValue === STATES.IDLE) {
            this.TOTAL_FORMSTarget.value = value;
        }
    }

    stateValueChanged (value, previousValue) {
        this.submitBtnState(value)
    }

    submitBtnState (state) {
        this.submitBtnTargets.forEach(it => {
            if (state === STATES.LOADING) {
                it.classList.add(this.loadingClass);
                it.setAttribute("disabled", "disabled");
            } else {
                it.classList.remove(this.loadingClass);
                it.removeAttribute("disabled");
            }
        })
    }

    modalOpenedValueChanged (value) {
        this.confirmationDialogTargets.forEach(it => {
            if (value) {
                dsfr(it).modal.disclose();
            } else {
                dsfr(it).modal.conceal();
            }
        });
    }

    async onPartialSubmit () {
        if (this.stateValue !== STATES.IDLE || !this.formTarget.reportValidity()) {
            return;
        }

        this.stateValue = STATES.LOADING;
        try {
            const response = await fetch(
                this.actionUrlValue,
                {method: "POST", body: new FormData(this.formTarget)}
            )
            if (response.status === 422) {  // Form has an error
                this.leftFormReplaceTarget.innerHTML = await response.text();
            } else if (response.ok) {  // Form is ok
                this.rightFormsInsertTarget.insertAdjacentHTML("beforeend", await response.text());
                this.validateAndResetLeftForm();
                this.showElement(this.rightFormsInsertContainerTarget)
            }
        } catch (e) {
            console.error(e)
        } finally {
            this.stateValue = STATES.IDLE
        }
    }

    /**
     *
     * @param onCancel {function(evt: Event):any | undefined}
     * @param onConfirm {function(evt: Event):any | undefined}
     */
    openDialog ({onCancel = undefined, onConfirm = undefined} = {}) {
        const cancelCb = evt => {
            evt.preventDefault();
            evt.stopPropagation();
            this.dialogCancelButtonTarget.removeEventListener("click", cancelCb);
            if (onCancel instanceof Function) {
                onCancel(evt);
            }
            this.modalOpenedValue = false;
        };
        this.dialogCancelButtonTarget.addEventListener("click", cancelCb);

        const confirmCB = evt => {
            evt.preventDefault();
            evt.stopPropagation();
            this.dialogConfirmButtonTarget.removeEventListener("click", confirmCB);
            if (onConfirm instanceof Function) {
                onConfirm(evt);
            }
            this.modalOpenedValue = false;
        };
        this.dialogConfirmButtonTarget.addEventListener("click", confirmCB);

        this.modalOpenedValue = true;
    }

    validateAndResetLeftForm () {
        this.leftFormReplaceTarget.innerHTML = this.formTplTarget.innerHTML.replace(
            /__prefix__/g, `${this.nbFormCountValue}`
        );
        this.nbFormCountValue = this.nbFormCountValue + 1;
    }
}

aidantsConnectApplicationReady.then(app => app.register("new-habilitation-request", NewHabilitationRequest))
