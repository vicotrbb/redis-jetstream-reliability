import Std

set_option autoImplicit false

/-!
Conditional abstract models accompanying the empirical Redis / JetStream paper.
All time quantities in the first section are integer ticks on one idealized axis.
This module does not model either broker implementation or establish that a
measured run satisfies the hypotheses. See README.md for the verification status.
-/

namespace DeliveryModel

/-! ## Residual timeout and the client-receipt offset -/

/-- Algebraic decomposition used by the paper's residual-time proof. -/
theorem residual_decomposition (d f delta selection observation : Int) :
    selection + observation - f =
      delta - (f - d) + (selection - (d + delta)) + observation := by
  omega

/-- Conditional integer-time counterpart of the residual recovery bound.
`selection` is broker/reclaimer selection; `observation` is a subsequent delay.
`P` and `B` are actual upper bounds, not nominal polling configuration values. -/
theorem residual_timeout_bound (d f delta selection observation P B : Int)
    (_hAgeNonnegative : 0 ≤ f - d)
    (hAgeBelow : f - d < delta)
    (hSelectLower : d + delta ≤ selection)
    (hSelectUpper : selection ≤ d + delta + P)
    (hObservationLower : 0 ≤ observation)
    (hObservationUpper : observation ≤ B) :
    0 < delta - (f - d) ∧
      delta - (f - d) ≤ selection + observation - f ∧
      selection + observation - f ≤ delta - (f - d) + P + B := by
  constructor
  · omega
  · constructor <;> omega

/-- Client receipt is `d + u`; observed redelivery is `d + delta + w + b`.
The identity itself needs no sign assumptions. -/
theorem observed_receipt_offset (d delta w b u : Int) :
    ((d + delta + w + b) - (d + u)) - delta = w + b - u := by
  omega

/-- Negative observed timer excess is compatible with nonnegative server delay:
it occurs when the initial receipt offset exceeds the later added delays. -/
theorem observed_excess_negative_iff (d delta w b u : Int) :
    ((d + delta + w + b) - (d + u)) - delta < 0 ↔ w + b < u := by
  omega

/-! ## Summed consumer capacity -/

/-- Each list entry is the total busy time of one consumer in a common window.
Per-consumer containment and nonoverlap justify the premise outside this lemma.
This is the integer, division-free core of `X * mean R ≤ C`. -/
theorem busy_sum_le_capacity (T : Nat) (busy : List Nat) :
    (∀ t ∈ busy, t ≤ T) → busy.sum ≤ busy.length * T := by
  induction busy with
  | nil =>
      intro _
      simp
  | cons t ts ih =>
      intro h
      have ht : t ≤ T := h t (by simp)
      have hTail : ∀ x ∈ ts, x ≤ T := by
        intro x hx
        exact h x (by simp [hx])
      have hSum := ih hTail
      simp only [List.sum_cons, List.length_cons, Nat.succ_mul]
      omega

/-- The same bound with an explicit consumer-count parameter. -/
theorem consumer_capacity (C T : Nat) (busy : List Nat)
    (hCount : busy.length = C) (hEach : ∀ t ∈ busy, t ≤ T) :
    busy.sum ≤ C * T := by
  have h := busy_sum_le_capacity T busy hEach
  simpa only [hCount] using h

/-! ## Separate external effects and broker acknowledgments

The broker and durable external-effect counter survive a consumer crash.
The restarted consumer loses its local payload. Redelivery is enabled only for
an unacknowledged message and does not deduplicate the external effect.
Acknowledgment deliberately does not erase an already-held local payload, so
both operation orders can succeed when the consumer does not crash.
-/

structure State where
  effects : Nat
  pending : Bool
  live : Bool
  hasPayload : Bool
  deriving DecidableEq, Repr

inductive Event where
  | effect
  | ack
  | crash
  | restart
  | redeliver
  deriving DecidableEq, Repr

/-- Invalid transitions return `none`; a successful run contains only enabled
transitions, not silent no-ops for invalid events. -/
def step (s : State) (event : Event) : Option State :=
  match event with
  | .effect =>
      if s.live && s.hasPayload then
        some { s with effects := s.effects + 1 }
      else none
  | .ack =>
      if s.live && s.hasPayload && s.pending then
        some { s with pending := false }
      else none
  | .crash =>
      if s.live then
        some { s with live := false, hasPayload := false }
      else none
  | .restart =>
      if s.live then none
      else some { s with live := true, hasPayload := false }
  | .redeliver =>
      if s.live && s.pending && !s.hasPayload then
        some { s with hasPayload := true }
      else none

def run : State → List Event → Option State
  | s, [] => some s
  | s, event :: events =>
      match step s event with
      | none => none
      | some next => run next events

/-- The initial message has already been delivered, but not acknowledged. -/
def initial : State :=
  { effects := 0, pending := true, live := true, hasPayload := true }

def onceState : State :=
  { effects := 1, pending := false, live := true, hasPayload := true }

def duplicateState : State :=
  { effects := 2, pending := false, live := true, hasPayload := true }

def lostEffectState : State :=
  { effects := 0, pending := false, live := true, hasPayload := false }

def effectFirstCrashTrace : List Event :=
  [.effect, .crash, .restart, .redeliver, .effect, .ack]

def ackFirstCrashTrace : List Event :=
  [.ack, .crash, .restart]

/-- Both orders can complete once when there is no consumer interruption. -/
theorem uninterrupted_orders :
    run initial [.effect, .ack] = some onceState ∧
      run initial [.ack, .effect] = some onceState := by
  exact ⟨rfl, rfl⟩

/-- A crash after the effect and before ACK leaves pending work; one legal retry
then completes the external effect a second time. -/
theorem effect_before_ack_crash :
    run initial effectFirstCrashTrace = some duplicateState ∧
      duplicateState.effects = 2 ∧ duplicateState.pending = false := by
  exact ⟨rfl, rfl, rfl⟩

/-- A crash after ACK and before the effect leaves zero effects and no pending
work. A redelivery transition is disabled even after the consumer restarts. -/
theorem ack_before_effect_crash :
    run initial ackFirstCrashTrace = some lostEffectState ∧
      lostEffectState.effects = 0 ∧ lostEffectState.pending = false ∧
      step lostEffectState .redeliver = none := by
  exact ⟨rfl, rfl, rfl, rfl⟩

inductive OperationOrder where
  | effectThenAck
  | ackThenEffect
  deriving DecidableEq, Repr

def crashTrace : OperationOrder → List Event
  | .effectThenAck => effectFirstCrashTrace
  | .ackThenEffect => ackFirstCrashTrace

def crashResult : OperationOrder → State
  | .effectThenAck => duplicateState
  | .ackThenEffect => lostEffectState

/-- Each of the two operation orders has an explicit valid crash execution with
no remaining broker obligation and an external-effect count different from one.
This says nothing about protocols adding transactions or durable deduplication. -/
theorem each_order_has_counterexample (order : OperationOrder) :
    run initial (crashTrace order) = some (crashResult order) ∧
      (crashResult order).pending = false ∧
      (crashResult order).effects ≠ 1 := by
  cases order <;> decide

end DeliveryModel

-- These commands expose the transitive logical dependencies during checking.
#print axioms DeliveryModel.residual_decomposition
#print axioms DeliveryModel.residual_timeout_bound
#print axioms DeliveryModel.observed_receipt_offset
#print axioms DeliveryModel.observed_excess_negative_iff
#print axioms DeliveryModel.busy_sum_le_capacity
#print axioms DeliveryModel.consumer_capacity
#print axioms DeliveryModel.uninterrupted_orders
#print axioms DeliveryModel.effect_before_ack_crash
#print axioms DeliveryModel.ack_before_effect_crash
#print axioms DeliveryModel.each_order_has_counterexample
