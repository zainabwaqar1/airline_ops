# Class diagram (item 4)

Paste the block below into any Mermaid renderer (Cursor previews Markdown with Mermaid;
https://mermaid.live also works). Inheritance is drawn with `<|--`; the main associations
with `-->`. Attribute lists are kept short on purpose - the Design tab of the console shows
the live, complete class list.

```mermaid
classDiagram
    direction LR

    class Record { id; status; created_at; events; log(); set_status(); archive() }
    class TemporalRecord { valid_from; valid_to; is_valid_at(t); end() }
    Record <|-- TemporalRecord

    %% ---- fleet
    class AircraftType { code; manufacturer; max_cargo_kg }
    class Aircraft { registration; msn; cargo_capacity_kg; location; current_configuration(); configuration_at(t) }
    class CabinConfiguration { name; version; cabins; seats; capacity() }
    class Seat { number; cabin_class }
    class Component { part_number; serial_number }
    Record <|-- AircraftType
    Record <|-- Aircraft
    TemporalRecord <|-- CabinConfiguration
    Record <|-- Seat
    TemporalRecord <|-- Component
    Aircraft --> AircraftType
    CabinConfiguration --> Aircraft
    Seat --> CabinConfiguration
    Component --> Aircraft

    %% ---- network
    class Airport { iata; operator; restrictions_at(t) }
    class AirportRestriction { kind; capacity_factor }
    class Route { origin; destination; international }
    class ScheduledService { flight_number; dep_time; days_of_week; service_kind }
    class Flight { date; std; etd; current_aircraft(); aircraft_at(t); crew_assignments(); segments() }
    class AircraftAssignment { reason; superseded_by }
    class FlightMovement { actual_departure; actual_arrival; actual_destination }
    Record <|-- Airport
    TemporalRecord <|-- AirportRestriction
    Record <|-- Route
    Record <|-- ScheduledService
    Record <|-- Flight
    TemporalRecord <|-- AircraftAssignment
    Record <|-- FlightMovement
    AirportRestriction --> Airport
    Route --> Airport
    ScheduledService --> Route
    Flight --> ScheduledService
    AircraftAssignment --> Flight
    AircraftAssignment --> Aircraft
    FlightMovement --> Flight

    %% ---- people (multi-level hierarchy)
    class Organisation { name; kind }
    class Person { first_name; last_name; date_of_birth; documents() }
    class Passenger { frequent_flyer; is_infant() }
    class Employee { staff_number; base; role_at(t); qualifications_at(t) }
    class CrewMember { max_duty_hours; position_location; qualified_for(type) }
    class FlightDeckCrew { licence_number }
    class CabinCrew { languages }
    class MaintenanceEngineer { authorisation; can_certify(type) }
    class GroundStaff { department }
    class RoleAssignment { title; department }
    class Qualification { kind; subject_code; issued_by }
    class CrewAssignment { position; role_title; replaced_by }
    class DutyPeriod { kind; location }
    Record <|-- Organisation
    Record <|-- Person
    Person <|-- Passenger
    Person <|-- Employee
    Employee <|-- CrewMember
    CrewMember <|-- FlightDeckCrew
    CrewMember <|-- CabinCrew
    Employee <|-- MaintenanceEngineer
    Employee <|-- GroundStaff
    TemporalRecord <|-- RoleAssignment
    TemporalRecord <|-- Qualification
    TemporalRecord <|-- CrewAssignment
    TemporalRecord <|-- DutyPeriod
    RoleAssignment --> Employee
    Qualification --> Employee
    CrewAssignment --> Flight
    CrewAssignment --> CrewMember
    DutyPeriod --> CrewMember

    %% ---- commercial
    class Booking { locator; booked_by; corporate }
    class FlightSegment { cabin_class; fare; rebooked_from; rebooked_to; connecting_to }
    class SeatAssignment { reason }
    class TravelDocument { kind; number; expires }
    class CheckIn { channel; boarding_pass_seq; offload_reason }
    class SpecialServiceRequest { code; detail }
    class CharterAgreement { agreed_passengers; price; amendments }
    Record <|-- Booking
    Record <|-- FlightSegment
    TemporalRecord <|-- SeatAssignment
    Record <|-- TravelDocument
    Record <|-- CheckIn
    Record <|-- SpecialServiceRequest
    Record <|-- CharterAgreement
    Booking --> Organisation
    FlightSegment --> Booking
    FlightSegment --> Passenger
    FlightSegment --> Flight
    SeatAssignment --> FlightSegment
    SeatAssignment --> Seat
    TravelDocument --> Person
    CheckIn --> FlightSegment
    SpecialServiceRequest --> FlightSegment
    CharterAgreement --> Organisation
    CharterAgreement --> Flight

    %% ---- baggage
    class Bag { tag; weight_kg; movements(); current_flight() }
    class BagMovement { reason; loaded_at; offloaded_at }
    class BaggageIrregularity { kind; resolution }
    Record <|-- Bag
    Record <|-- BagMovement
    Record <|-- BaggageIrregularity
    Bag --> FlightSegment
    BagMovement --> Bag
    BagMovement --> Flight
    BaggageIrregularity --> Bag

    %% ---- cargo
    class Consignment { awb_number; pieces; weight_kg; accepted_at; requirements(at) }
    class HandlingRequirement { code; detail; declared_by }
    class CargoLoad { loaded_at; offloaded_at; offload_reason }
    Record <|-- Consignment
    TemporalRecord <|-- HandlingRequirement
    Record <|-- CargoLoad
    Consignment --> Organisation
    HandlingRequirement --> Consignment
    CargoLoad --> Consignment
    CargoLoad --> Flight

    %% ---- maintenance
    class EngineeringRecord { description; certified_by; closed_at; close() }
    class Inspection { check_type; findings }
    class Defect { ata_chapter; grounding; mel_reference; deferral_expires }
    class WorkOrder { due_at; estimated_hours }
    Record <|-- EngineeringRecord
    EngineeringRecord <|-- Inspection
    EngineeringRecord <|-- Defect
    EngineeringRecord <|-- WorkOrder
    EngineeringRecord --> Aircraft
    EngineeringRecord --> MaintenanceEngineer
    Defect --> Component
    Defect --> Inspection
    WorkOrder --> Defect

    %% ---- disruption
    class Disruption { reason_code; declared_at; resolution; affected; resolve(); options() }
    class Delay { minutes; knock_on }
    class Cancellation { records_preserved }
    class Diversion { diverted_to }
    class AircraftSubstitution { from_aircraft; to_aircraft; seats_lost; cargo_offloaded_kg }
    class RecoveryOption { description; cost_estimate; decided_by }
    Record <|-- Disruption
    Disruption <|-- Delay
    Disruption <|-- Cancellation
    Disruption <|-- Diversion
    Disruption <|-- AircraftSubstitution
    Record <|-- RecoveryOption
    Disruption --> Flight
    RecoveryOption --> Disruption
```
