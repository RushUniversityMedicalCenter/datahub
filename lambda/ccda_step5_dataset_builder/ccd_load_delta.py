import pandas as pd
import os
import json
import boto3


def getValueFromDict(dataVal, dictKey):
    return dataVal.get(dictKey)


def getComposition(dataRecord):
    composition = {}
    for i in dataRecord['entry']:
        i_resource = getValueFromDict(i, 'resource')
        i_resourceType = getValueFromDict(i_resource, 'resourceType')
        if i_resourceType == 'Composition':
            composition['comp_id'] = i_resource['id']
            i_res_type = getValueFromDict(i_resource['type'], 'coding')
            composition['doc_type'] = i_res_type[0]['display']
    return composition


def getPatientData(dataRecord, filename):
    personList = []
    composition = getComposition(dataRecord)
    orgName = ''

    if 'entry' not in dataRecord:
        raise KeyError("entry key is missing")
    else:
        for i in dataRecord['entry']:

            i_resource = i.get('resource')
            i_resourceType = i_resource.get('resourceType')
            if i_resourceType == 'Organization':
                orgName = orgName + i_resource.get('name') + ' '

        for i in dataRecord['entry']:
            person = {}
            i_resource = i.get('resource')
            i_resourceType = i_resource.get('resourceType')

            if i_resourceType == 'Patient':
                person['person_id'] = i_resource.get('id')
                person['birthdate'] = i_resource.get('birthDate')
                person['gender'] = i_resource.get('gender')

                i_name = i_resource.get('name')
                for name in i_name:
                    name_use = name.get('use')
                    if name_use == 'usual':
                        person['lastname'] = name['family']
                        person['firstname'] = name['given'][0]
                i_extension = getValueFromDict(i_resource, 'extension')
                for values in i_extension:
                    if getValueFromDict(values, 'url') == 'http://hl7.org/fhir/us/core/StructureDefinition/us-core-race':
                        values_extension = getValueFromDict(
                            values, 'extension')
                        for race in values_extension:
                            if getValueFromDict(race, 'url') == 'text':
                                person['raceVal'] = race['valueString']

                    if getValueFromDict(values, 'url') == 'http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity':
                        values_extension = getValueFromDict(
                            values, 'extension')
                        for ethnicity in values_extension:
                            if getValueFromDict(ethnicity, 'url') == 'text':
                                person['ethVal'] = ethnicity['valueString']

                i_address = getValueFromDict(i_resource, 'address')
                if i_address:
                    for address in i_address:
                        if getValueFromDict(address, 'use') == 'home':
                            person['address'] = getValueFromDict(
                                address, 'line')[0]
                            person['city'] = address['city']
                            person['state'] = address['state']
                            if 'country' in address:
                                person['country'] = address['country']
                            if 'postalCode' in address:
                                person['postalCode'] = address['postalCode']
                person['filename'] = filename
                person['orgName'] = orgName
                person['doc_id'] = composition['comp_id']
                person['doc_type'] = composition['doc_type']
                personList.append(person)

    return personList


def getEncounterRecord(dataRecord, filename):
    encounterList = []
    orgName = ''
    composition = getComposition(dataRecord)
    for i in dataRecord['entry']:

        i_resource = i.get('resource')
        i_resourceType = i_resource.get('resourceType')
        if i_resourceType == 'Patient':
            person_id = i_resource['id']
        if i_resourceType == 'Organization':
            orgName = orgName + getValueFromDict(i_resource, 'name') + ' '

    for j in dataRecord['entry']:
        encounter = {}
        j_resource = getValueFromDict(j, 'resource')
        j_resourceType = getValueFromDict(j_resource, 'resourceType')
        if j_resourceType == 'Encounter':
            encounter['person_id'] = person_id
            encounter['encounter_id'] = j_resource['id']
            j_class = getValueFromDict(j_resource, 'class')
            encounter['class'] = getValueFromDict(j_class, 'display')
            j_encounter_type = getValueFromDict(j_resource, 'type')
            if j_encounter_type:
                encounter['type'] = j_encounter_type[0]['coding'][0]['display']
            j_period = getValueFromDict(j_resource, 'period')
            if j_period:
                encounter['start'] = getValueFromDict(j_period, 'start')
                encounter['end'] = getValueFromDict(j_period, 'end')
            j_hosp = getValueFromDict(j_resource, 'hospitalization')
            j_dcdispo = getValueFromDict(j_hosp, 'dischargeDisposition')
            if j_dcdispo:
                encounter['dcDispo'] = j_dcdispo['coding'][0]['display']
            encounter['filename'] = filename
            encounter['orgName'] = orgName
            encounter['doc_id'] = composition['comp_id']
            encounter['doc_type'] = composition['doc_type']
            encounterList.append(encounter)

    return encounterList


def getConditionRecord(dataRecord, filename):
    conditionList = []
    encounter_id = ''
    orgName = ''
    composition = getComposition(dataRecord)
    for i in dataRecord['entry']:
        i_resource = getValueFromDict(i, 'resource')
        i_resourceType = getValueFromDict(i_resource, 'resourceType')
        if i_resourceType == 'Patient':
            person_id = i_resource['id']
        if i_resourceType == 'Encounter':
            encounter_id = i_resource['id']
        if i_resourceType == 'Organization':
            orgName = orgName + getValueFromDict(i_resource, 'name') + ' '
    for j in dataRecord['entry']:
        j_resource = getValueFromDict(j, 'resource')
        j_resourceType = getValueFromDict(j_resource, 'resourceType')
        if j_resourceType == 'Condition':
            j_code = getValueFromDict(j_resource, 'code')
            if j_code:
                for dxcode in j_code['coding']:
                    condition = {}
                    condition['person_id'] = person_id
                    condition['encounter_id'] = encounter_id
                    condition['dxcode'] = dxcode['code']
                    condition['dxdescription'] = dxcode['display']
                    condition['dxsystem'] = dxcode['system']
                    condition['filename'] = filename
                    condition['orgName'] = orgName
                    condition['doc_id'] = composition['comp_id']
                    condition['doc_type'] = composition['doc_type']
                    conditionList.append(condition)
    return conditionList


def getMedicationRecord(dataRecord, filename):
    medicationList = []
    encounter_id = ''
    orgName = ''
    composition = getComposition(dataRecord)
    for i in dataRecord['entry']:
        i_resource = getValueFromDict(i, 'resource')
        i_resourceType = getValueFromDict(i_resource, 'resourceType')
        if i_resourceType == 'Patient':
            person_id = i_resource['id']
        if i_resourceType == 'Encounter':
            encounter_id = i_resource['id']
        if i_resourceType == 'Organization':
            orgName = orgName + getValueFromDict(i_resource, 'name') + ' '

    for j in dataRecord['entry']:
        j_resource = getValueFromDict(j, 'resource')
        j_resourceType = getValueFromDict(j_resource, 'resourceType')
        if j_resourceType == 'Medication':
            j_code = getValueFromDict(j_resource, 'code')
            if j_code:
                for medication in j_code['coding']:
                    medications = {}
                    medications['record_type'] = 'Medication'
                    medications['person_id'] = person_id
                    medications['encounter_id'] = encounter_id
                    medications['code'] = getValueFromDict(medication, 'code')
                    medications['drug_name'] = getValueFromDict(
                        medication, 'display')
                    medications['code_system'] = getValueFromDict(
                        medication, 'system')
                    medications['filename'] = filename
                    medications['orgName'] = orgName
                    medications['doc_id'] = composition['comp_id']
                    medications['doc_type'] = composition['doc_type']
                    medicationList.append(medications)
    return medicationList


def getObservationRecord(dataRecord, filename):
    observationList = []
    encounter_id = ''
    orgName = ''
    composition = getComposition(dataRecord)
    for i in dataRecord['entry']:
        i_resource = getValueFromDict(i, 'resource')
        i_resourceType = getValueFromDict(i_resource, 'resourceType')
        if i_resourceType == 'Patient':
            person_id = i_resource['id']
        if i_resourceType == 'Encounter':
            encounter_id = i_resource['id']
        if i_resourceType == 'Organization':
            orgName = orgName + getValueFromDict(i_resource, 'name') + ' '
    for j in dataRecord['entry']:
        j_resource = getValueFromDict(j, 'resource')
        j_resourceType = getValueFromDict(j_resource, 'resourceType')
        if j_resourceType == 'Observation':
            status = getValueFromDict(j_resource, 'status')
            testDate = getValueFromDict(j_resource, 'effectiveDateTime')
            testInterpList = getValueFromDict(j_resource, 'interpretation')
            if testInterpList:
                # print('present')
                testInterp = testInterpList[0]['coding'][0]['code']
#                testInterp = testInterpList
            else:
                testInterp = ''
            j_code = getValueFromDict(j_resource, 'code')
            if j_code:
                for observation in j_code['coding']:
                    observations = {}
                    observations['record_type'] = 'Observation'
                    observations['person_id'] = person_id
                    observations['encounter_id'] = encounter_id
                    observations['code'] = getValueFromDict(
                        observation, 'code')
                    observations['test_name'] = getValueFromDict(
                        observation, 'display')
                    observations['code_system'] = getValueFromDict(
                        observation, 'system')
                    observations['testInterp'] = testInterp
                    observations['testDate'] = testDate
                    observations['status'] = status
                    observations['filename'] = filename
                    observations['orgName'] = orgName
                    observations['doc_id'] = composition['comp_id']
                    observations['doc_type'] = composition['doc_type']
                    observationList.append(observations)

    return observationList


def build_datasets(fhir_json, filename):
    filelist = []
    datalist = []
    persons = []
    encounters = []
    medications = []
    observationdata = []
    conditions = []

    patientList = getPatientData(fhir_json, filename)
    persons.extend(patientList)
    encounterList = getEncounterRecord(fhir_json, filename)
    encounters.extend(encounterList)
    conditionList = getConditionRecord(fhir_json, filename)
    conditions.extend(conditionList)
    medicationList = getMedicationRecord(fhir_json, filename)
    medications.extend(medicationList)
    observationList = getObservationRecord(fhir_json, filename)
    observationdata.extend(observationList)

    df_persons = pd.DataFrame(persons)
    df_encounters = pd.DataFrame(encounters)
    df_conditions = pd.DataFrame(conditions)
    df_medications = pd.DataFrame(medications)
    df_observations = pd.DataFrame(observationdata)

    datasets = {
        "person": df_persons,
        "encounters": df_encounters,
        "conditions": df_conditions,
        "medications": df_medications,
        "observations": df_observations,
    }

    return datasets
