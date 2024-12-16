import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

const STATES = Object.freeze({
    NOT_READY: "NOT_READY",
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
 */
class NewHabilitationRequest extends BaseController {
    static targets = [
        "form",
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
        state: {type: String, default: STATES.NOT_READY},
        nbFormCount: {type: Number, default: -1},
        modalOpened: {type: Boolean, default: false},
    }
    static classes = ["loading", "submitBtnEdit", "submitBtnValidate"]

    initialize () {
        this.nbFormCountValue = Number.parseInt(this.TOTAL_FORMSTarget.value)
        this.stateValue = STATES.IDLE
    }

    nbFormCountValueChanged (value) {
        if (this.stateValue === STATES.IDLE) {
            this.TOTAL_FORMSTarget.value = value;
        }
    }

    stateValueChanged (value, previousValue) {
        if (previousValue === STATES.NOT_READY) {
            this.showElement(this.formTarget)
        }
        this.submitBtnState(value)
    }

    submitBtnState (state) {
        this.submitBtnTargets.forEach(it => {
            if (state === STATES.IDLE) {
                it.classList.remove(this.loadingClass);
                it.removeAttribute("disabled");
            } else if (state === STATES.LOADING) {
                it.classList.add(this.loadingClass);
                it.setAttribute("disabled", "disabled");
            }
        })
    }

    modalOpenedValueChanged (value) {
        this.confirmationDialogTargets.forEach(it => {
            try {
                if (value) {
                    dsfr(it).modal.disclose();
                } else {
                    dsfr(it).modal.conceal();
                }
            } catch {/* Do nothing */}
        });
    }

    async onPartialSubmit () {
        if (this.stateValue !== STATES.IDLE || !this.formTarget.reportValidity()) {
            return;
        }

        this.stateValue = STATES.LOADING;
        try {
            const response = await fetch(
                Urls.apiEspaceResponsableAidantNew(),
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

aidantsConnectApplicationReady.then(application => application.register("new-habilitation-request", NewHabilitationRequest));
