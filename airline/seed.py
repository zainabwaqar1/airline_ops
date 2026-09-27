"""
Seed one operating day: Thursday 24 September 2026, starting at 04:00.

Everything the scenario demos need is created here through the normal
operations, so the seed itself exercises the model.  Returns the registry
plus a dict of handles the demos use by name.
"""
from datetime import date, datetime
from .core import Registry, set_clock
from .fleet import AircraftType
from .people import Organisation, Passenger
from . import operations as op

DAY = date(2026, 9, 24)


def T(hh, mm=0):
    return datetime(DAY.year, DAY.month, DAY.day, hh, mm)


def build():
    set_clock(T(4, 0))
    reg = Registry()
    h = {}   # handles

    # ---------------------------------------------------------------- airports
    apts = {}
    for iata, name, city, country, oper in [
        ("LHE", "Allama Iqbal International", "Lahore", "PK", "Pakistan Airports Authority"),
        ("KHI", "Jinnah International", "Karachi", "PK", "Pakistan Airports Authority"),
        ("ISB", "Islamabad International", "Islamabad", "PK", "Pakistan Airports Authority"),
        ("SKZ", "Sukkur", "Sukkur", "PK", "Pakistan Airports Authority"),
        ("MUX", "Multan International", "Multan", "PK", "Pakistan Airports Authority"),
        ("DXB", "Dubai International", "Dubai", "AE", "Dubai Airports"),
    ]:
        from .network import Airport
        apts[iata] = Airport(reg, iata, name, city, country, oper)
        apts[iata].log("registered", name)
    h["apts"] = apts

    # ---------------------------------------------------------------- organisations
    orgs = {
        "swift": Organisation(reg, "SwiftFreight Agents", "freight_agent"),
        "pharma": Organisation(reg, "PharmaCo Pakistan", "shipper"),
        "machines": Organisation(reg, "Indus Machine Works", "shipper"),
        "textiles": Organisation(reg, "Nishat Textiles", "shipper"),
        "corp": Organisation(reg, "Engro Travel Desk", "corporate"),
        "charter_cust": Organisation(reg, "Sukkur Textile Mills", "charter_customer"),
        "handler_khi": Organisation(reg, "Gerry's dnata (KHI handler)", "handler"),
    }
    h["orgs"] = orgs

    # ---------------------------------------------------------------- fleet
    a320 = AircraftType(reg, "A320", "Airbus", "A320-200", 3000, 6100)
    atr = AircraftType(reg, "ATR72", "ATR", "ATR 72-500", 800, 1500)
    ac = {}
    ac["BHA"] = op.register_aircraft(reg, "AP-BHA", "A320", 4411, 3000, "12C/150Y", [("C", 3, 4), ("Y", 25, 6)])
    ac["BHB"] = op.register_aircraft(reg, "AP-BHB", "A320", 4587, 1600, "8C/138Y", [("C", 2, 4), ("Y", 23, 6)])
    ac["BHD"] = op.register_aircraft(reg, "AP-BHD", "A320", 5120, 2600, "174Y all-economy", [("Y", 29, 6)])
    ac["BHC"] = op.register_aircraft(reg, "AP-BHC", "A320", 4702, 3000, "12C/150Y", [("C", 3, 4), ("Y", 25, 6)])
    ac["BHE"] = op.register_aircraft(reg, "AP-BHE", "A320", 3990, 3000, "12C/156Y", [("C", 3, 4), ("Y", 26, 6)])
    ac["BKX"] = op.register_aircraft(reg, "AP-BKX", "ATR72", 812, 800, "72Y", [("Y", 18, 4)])
    for k, loc in [("BHA", "LHE"), ("BHB", "LHE"), ("BHD", "LHE"), ("BHC", "ISB"), ("BHE", "LHE"), ("BKX", "LHE")]:
        ac[k].location = apts[loc]
    h["ac"] = ac
    h["apu_bhb"] = op.install_component(reg, ac["BHB"], "APS3200", "E-2231", "Auxiliary power unit")
    h["eng1_bha"] = op.install_component(reg, ac["BHA"], "CFM56-5B", "779311", "Engine #1")

    # ---------------------------------------------------------------- staff
    E = {}
    def hire(key, kind, fn, ln, dob, staff, base, title, dept, extra):
        E[key] = op.hire_employee(reg, kind, fn, ln, date(*dob), "PK", staff, apts[base], title, dept, extra)
    hire("raza", "flight_deck", "Ahmed", "Raza", (1979, 3, 2), "P1001", "LHE", "Captain", "Flight Operations", "ATPL-4471")
    hire("khan", "flight_deck", "Sara", "Khan", (1990, 7, 19), "P1002", "LHE", "First Officer", "Flight Operations", "CPL-8820")
    hire("chaudhry", "flight_deck", "Bilal", "Chaudhry", (1976, 11, 5), "P1003", "LHE", "Captain", "Flight Operations", "ATPL-3310")
    hire("qureshi", "flight_deck", "Danish", "Qureshi", (1981, 1, 28), "P1004", "LHE", "Captain", "Flight Operations", "ATPL-5102")
    hire("tariq", "flight_deck", "Usman", "Tariq", (1992, 5, 9), "P1005", "LHE", "First Officer", "Flight Operations", "CPL-9911")
    hire("shah", "flight_deck", "Imran", "Shah", (1978, 9, 14), "P1006", "ISB", "Captain", "Flight Operations", "ATPL-4090")
    hire("iqbal", "flight_deck", "Zara", "Iqbal", (1991, 2, 3), "P1007", "ISB", "First Officer", "Flight Operations", "CPL-9002")
    hire("farooq", "flight_deck", "Omar", "Farooq", (1983, 6, 21), "P1008", "LHE", "Captain", "Flight Operations", "ATPL-4720")
    hire("baig", "flight_deck", "Hina", "Baig", (1993, 12, 1), "P1009", "LHE", "First Officer", "Flight Operations", "CPL-9350")
    hire("hussain", "cabin", "Nadia", "Hussain", (1986, 4, 11), "C2001", "LHE", "Senior Cabin Crew", "Cabin Services", ["ur", "en"])
    hire("ali", "cabin", "Hamza", "Ali", (1995, 8, 30), "C2002", "LHE", "Cabin Crew", "Cabin Services", ["ur", "en"])
    hire("malik", "cabin", "Ayesha", "Malik", (1994, 10, 17), "C2003", "LHE", "Cabin Crew", "Cabin Services", ["ur", "en", "sd"])
    hire("siddiqui_f", "cabin", "Farhan", "Siddiqui", (1988, 2, 25), "C2004", "ISB", "Senior Cabin Crew", "Cabin Services", ["ur", "en", "ar"])
    hire("noor", "cabin", "Noor", "Fatima", (1996, 3, 8), "C2005", "ISB", "Cabin Crew", "Cabin Services", ["ur", "en"])
    hire("mehmood", "engineer", "Tariq", "Mehmood", (1975, 5, 5), "E3001", "LHE", "Licensed Engineer B1", "Engineering", "B1")
    hire("anwar", "engineer", "Kashif", "Anwar", (1984, 9, 9), "E3002", "LHE", "Licensed Engineer B2", "Engineering", "B2")
    hire("hassan", "ground", "Ali", "Hassan", (1987, 1, 15), "G4001", "LHE", "Dispatcher", "Operations Control", "dispatch")
    hire("mirza", "ground", "Sana", "Mirza", (1998, 6, 6), "G4002", "LHE", "Check-in Agent", "Passenger Services", "check_in")
    hire("karim", "ground", "Rashid", "Karim", (1982, 7, 7), "G4003", "LHE", "Cargo Supervisor", "Cargo", "cargo")
    hire("gill", "ground", "Maria", "Gill", (1985, 11, 23), "G4004", "KHI", "Duty Manager", "Operations Control", "ops_control")
    h["E"] = E

    # qualifications
    q = lambda who, kind, code, by="CAA Pakistan": op.grant_qualification(reg, E[who], kind, code, by)
    for who in ("raza", "khan", "qureshi", "tariq", "shah", "iqbal"):
        q(who, "type_rating", "A320")
    q("chaudhry", "type_rating", "ATR72")          # Captain title, but no A320 rating
    q("farooq", "type_rating", "ATR72"); q("baig", "type_rating", "ATR72")
    for who in ("hussain", "ali", "siddiqui_f", "noor"):
        q(who, "cabin_type", "A320", "Airline Training")
    h["malik_a320"] = q("malik", "cabin_type", "A320", "Airline Training")
    q("malik", "cabin_type", "ATR72", "Airline Training")
    q("mehmood", "certifying", "A320", "Airline Quality")
    q("mehmood", "certifying", "ATR72", "Airline Quality")
    q("anwar", "certifying", "ATR72", "Airline Quality")   # cannot certify A320
    op.roster_duty(reg, E["qureshi"], "standby", T(4, 0), T(12, 0), apts["LHE"])
    op.roster_duty(reg, E["tariq"], "rest", T(0, 0), T(9, 0), apts["LHE"])

    # ---------------------------------------------------------------- schedule
    svc = {}
    svc["301"] = op.create_scheduled_service(reg, "PK301", apts["LHE"], apts["KHI"], "05:30", "07:15", "1234567")
    svc["302"] = op.create_scheduled_service(reg, "PK302", apts["KHI"], apts["LHE"], "09:00", "10:45", "1234567")
    svc["760"] = op.create_scheduled_service(reg, "PK760", apts["ISB"], apts["KHI"], "07:00", "09:00", "1234567")
    svc["305"] = op.create_scheduled_service(reg, "PK305", apts["KHI"], apts["DXB"], "12:00", "14:30", "1234567")
    svc["9001"] = op.create_scheduled_service(reg, "PK9001", apts["LHE"], apts["SKZ"], "15:00", "16:15", "4", "charter")
    svc["303"] = op.create_scheduled_service(reg, "PK303", apts["LHE"], apts["KHI"], "18:00", "19:45", "1234567")
    svc["304"] = op.create_scheduled_service(reg, "PK304", apts["KHI"], apts["LHE"], "20:00", "21:45", "1234567")
    F = {}
    F["301"] = op.create_flight(reg, svc["301"], DAY, ac["BHA"])
    F["302"] = op.create_flight(reg, svc["302"], DAY, ac["BHA"])
    F["760"] = op.create_flight(reg, svc["760"], DAY, ac["BHC"])
    F["305"] = op.create_flight(reg, svc["305"], DAY, ac["BHC"])
    F["9001"] = op.create_flight(reg, svc["9001"], DAY, ac["BKX"])
    F["303"] = op.create_flight(reg, svc["303"], DAY, ac["BHE"])
    F["304"] = op.create_flight(reg, svc["304"], DAY, ac["BHD"])
    h["F"] = F

    # ---------------------------------------------------------------- crew assignments
    CA = {}
    for fl, who, pos in [("301", "raza", "CP"), ("301", "khan", "FO"), ("301", "hussain", "SCCM"), ("301", "ali", "CC"),
                         ("302", "raza", "CP"), ("302", "khan", "FO"), ("302", "hussain", "SCCM"), ("302", "ali", "CC"),
                         ("760", "shah", "CP"), ("760", "iqbal", "FO"), ("760", "siddiqui_f", "SCCM"), ("760", "noor", "CC"),
                         ("305", "shah", "CP"), ("305", "iqbal", "FO"), ("305", "siddiqui_f", "SCCM"), ("305", "noor", "CC"),
                         ("9001", "farooq", "CP"), ("9001", "baig", "FO"), ("9001", "malik", "SCCM"),
                         ("303", "raza", "CP"), ("303", "khan", "FO"), ("303", "hussain", "SCCM"), ("303", "ali", "CC")]:
        CA[(fl, who)] = op.assign_crew(reg, F[fl], E[who], pos)
    h["CA"] = CA

    # maintenance already planned for the day
    h["wo_bhb"] = op.open_work_order(reg, ac["BHB"], E["mehmood"], "Replace #2 brake unit (scheduled)", T(14, 0), 3.0)

    # ---------------------------------------------------------------- passengers
    P = {}
    def pax(key, fn, ln, dob, nat="PK", ff=None):
        P[key] = Passenger(reg, fn, ln, date(*dob), nat, ff)
        P[key].log("created", "profile")
    pax("ahmad", "Ahmad", "Siddiqui", (1980, 4, 4), ff="PK883211")
    pax("fatima", "Fatima", "Siddiqui", (1984, 8, 8))
    pax("baby", "Zain", "Siddiqui", (2025, 12, 1))              # infant
    pax("m_iqbal", "Mohammad", "Iqbal", (1948, 2, 14))         # mobility assistance
    pax("a_iqbal", "Ayesha", "Iqbal", (1952, 6, 30))
    pax("smith", "Jonathan", "Smith", (1975, 9, 9), "GB")
    pax("nadeem", "Nadeem", "Akhtar", (1990, 1, 1))
    pax("hira", "Hira", "Yousaf", (1993, 3, 3))
    pax("bilal_p", "Bilal", "Ahmed", (1988, 5, 5))
    pax("sadia", "Sadia", "Rehman", (1979, 7, 7))
    pax("omar_p", "Omar", "Sheikh", (1966, 10, 10))
    pax("laila", "Laila", "Noor", (2001, 11, 11))
    pax("kamran", "Kamran", "Butt", (1983, 12, 12))
    pax("zeeshan", "Zeeshan", "Haider", (1995, 4, 20))
    pax("rabia", "Rabia", "Aslam", (1989, 9, 19))
    pax("faisal", "Faisal", "Javed", (1972, 2, 2))
    h["P"] = P
    h["passport_ahmad"] = op.add_travel_document(reg, P["ahmad"], "passport", "AB1234567", "PK", date(2026, 10, 15))
    op.add_travel_document(reg, P["fatima"], "passport", "AB7654321", "PK", date(2031, 1, 1))
    op.add_travel_document(reg, P["baby"], "passport", "AB9999999", "PK", date(2030, 1, 1))
    op.add_travel_document(reg, P["smith"], "passport", "GB55512345", "GB", date(2029, 6, 1))
    op.add_travel_document(reg, P["nadeem"], "passport", "AB2223334", "PK", date(2032, 1, 1))

    # bookings on PK301 (the 05:30 flight)
    S = {}
    b1 = op.create_booking(reg, "ABC123", "Ahmad Siddiqui", "ahmad@example.com", orgs["corp"])
    S["ahmad_301"] = op.add_segment(reg, b1, P["ahmad"], F["301"], "C", 24000)
    S["fatima_301"] = op.add_segment(reg, b1, P["fatima"], F["301"], "C", 24000)
    S["baby_301"] = op.add_segment(reg, b1, P["baby"], F["301"], "INF", 2400)
    S["ahmad_305"] = op.add_segment(reg, b1, P["ahmad"], F["305"], "C", 61000, connecting_from=S["ahmad_301"])
    S["fatima_305"] = op.add_segment(reg, b1, P["fatima"], F["305"], "C", 61000, connecting_from=S["fatima_301"])
    S["baby_305"] = op.add_segment(reg, b1, P["baby"], F["305"], "INF", 6100, connecting_from=S["baby_301"])
    op.assign_seat(reg, S["ahmad_301"], "2A"); op.assign_seat(reg, S["fatima_301"], "2B")
    op.assign_seat(reg, S["ahmad_305"], "1A"); op.assign_seat(reg, S["fatima_305"], "1B")
    op.add_special_service(reg, S["baby_301"], "INFT", "infant on lap of Fatima Siddiqui")
    op.add_special_service(reg, S["baby_305"], "INFT", "infant on lap of Fatima Siddiqui")

    b2 = op.create_booking(reg, "DEF456", "Ayesha Iqbal", "iqbal@example.com")
    S["m_iqbal_301"] = op.add_segment(reg, b2, P["m_iqbal"], F["301"], "Y", 9500)
    S["a_iqbal_301"] = op.add_segment(reg, b2, P["a_iqbal"], F["301"], "Y", 9500)
    op.assign_seat(reg, S["m_iqbal_301"], "5C"); op.assign_seat(reg, S["a_iqbal_301"], "5D")
    op.add_special_service(reg, S["m_iqbal_301"], "WCHR", "wheelchair to aircraft door, can climb stairs")

    b3 = op.create_booking(reg, "GHI789", "Jonathan Smith", "jsmith@example.co.uk")
    S["smith_301"] = op.add_segment(reg, b3, P["smith"], F["301"], "Y", 9800)
    S["smith_305"] = op.add_segment(reg, b3, P["smith"], F["305"], "Y", 38000, connecting_from=S["smith_301"])
    op.assign_seat(reg, S["smith_301"], "27A"); op.assign_seat(reg, S["smith_305"], "10A")

    b4 = op.create_booking(reg, "JKL012", "Nadeem Akhtar", "nadeem@example.com")
    S["nadeem_301"] = op.add_segment(reg, b4, P["nadeem"], F["301"], "Y", 9200)
    S["hira_301"] = op.add_segment(reg, b4, P["hira"], F["301"], "Y", 9200)
    op.assign_seat(reg, S["nadeem_301"], "28C"); op.assign_seat(reg, S["hira_301"], "28D")

    b5 = op.create_booking(reg, "MNO345", "Bilal Ahmed", "bilal@example.com")
    S["bilal_301"] = op.add_segment(reg, b5, P["bilal_p"], F["301"], "Y", 9000)
    op.assign_seat(reg, S["bilal_301"], "12F")

    # bookings on PK760 (inbound from Islamabad) connecting to PK305
    b6 = op.create_booking(reg, "PQR678", "Sadia Rehman", "sadia@example.com")
    S["sadia_760"] = op.add_segment(reg, b6, P["sadia"], F["760"], "Y", 8800)
    S["sadia_305"] = op.add_segment(reg, b6, P["sadia"], F["305"], "Y", 37000, connecting_from=S["sadia_760"])
    op.assign_seat(reg, S["sadia_760"], "8A"); op.assign_seat(reg, S["sadia_305"], "12C")
    b7 = op.create_booking(reg, "STU901", "Omar Sheikh", "omar@example.com")
    S["omar_760"] = op.add_segment(reg, b7, P["omar_p"], F["760"], "Y", 8800)
    op.assign_seat(reg, S["omar_760"], "9B")

    # bookings on PK302 (the return, to be cancelled)
    b8 = op.create_booking(reg, "VWX234", "Laila Noor", "laila@example.com")
    S["laila_302"] = op.add_segment(reg, b8, P["laila"], F["302"], "Y", 9100)
    S["kamran_302"] = op.add_segment(reg, b8, P["kamran"], F["302"], "Y", 9100)
    op.assign_seat(reg, S["laila_302"], "6A"); op.assign_seat(reg, S["kamran_302"], "6B")

    # bookings on PK303 (evening) - used by the reconfiguration / retirement demo
    b9 = op.create_booking(reg, "YZA567", "Zeeshan Haider", "zeeshan@example.com")
    S["zeeshan_303"] = op.add_segment(reg, b9, P["zeeshan"], F["303"], "Y", 9400)
    S["rabia_303"] = op.add_segment(reg, b9, P["rabia"], F["303"], "Y", 9400)
    S["faisal_303"] = op.add_segment(reg, b9, P["faisal"], F["303"], "C", 23000)
    op.assign_seat(reg, S["zeeshan_303"], "29A"); op.assign_seat(reg, S["rabia_303"], "29B")
    op.assign_seat(reg, S["faisal_303"], "3A")
    h["S"] = S

    # early check-ins (online) and bags
    op.check_in_passenger(reg, S["m_iqbal_301"], None, "online"); op.check_in_passenger(reg, S["a_iqbal_301"], None, "online")
    op.check_in_passenger(reg, S["smith_301"], E["mirza"], "counter")
    op.check_in_passenger(reg, S["sadia_760"], None, "online"); op.check_in_passenger(reg, S["omar_760"], None, "online")
    h["bag_m_iqbal"] = op.accept_bag(reg, S["m_iqbal_301"], "PK301001", 18, E["mirza"])
    h["bag_a_iqbal"] = op.accept_bag(reg, S["a_iqbal_301"], "PK301002", 21, E["mirza"])
    h["bag_smith"] = op.accept_bag(reg, S["smith_301"], "PK301003", 23, E["mirza"])
    h["bag_omar"] = op.accept_bag(reg, S["omar_760"], "PK760001", 25, orgs["handler_khi"])

    # ---------------------------------------------------------------- cargo on PK301 and PK303
    C = {}
    C["pharma"] = op.book_consignment(reg, "214-11112222", orgs["pharma"], orgs["swift"], "Insulin, 40 cartons", 40, 400, apts["LHE"], apts["KHI"])
    op.declare_handling(reg, C["pharma"], "PER", "keep 2-8 C, cool-chain container", "SwiftFreight")
    C["textiles"] = op.book_consignment(reg, "214-55556666", orgs["textiles"], orgs["swift"], "Woven fabric rolls", 60, 1500, apts["LHE"], apts["KHI"])
    C["machines"] = op.book_consignment(reg, "214-33334444", orgs["machines"], orgs["swift"], "Machine parts (declared general cargo)", 12, 900, apts["LHE"], apts["KHI"])
    h["load_pharma"] = op.accept_consignment(reg, C["pharma"], E["karim"], F["301"])
    h["load_textiles"] = op.accept_consignment(reg, C["textiles"], E["karim"], F["301"])
    h["load_machines"] = op.accept_consignment(reg, C["machines"], E["karim"], F["303"])
    h["C"] = C

    # ---------------------------------------------------------------- charter agreement
    h["charter"] = op.create_charter_agreement(reg, orgs["charter_cust"], F["9001"], 60, 1850000)

    reg.seed_handles = h
    return reg, h
