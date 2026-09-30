package br.edu.insper.videoinsight.job.domain;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/** Guarda a lista de operações como texto separado por vírgulas. */
@Converter
public class OperationsConverter implements AttributeConverter<List<Operation>, String> {
    @Override
    public String convertToDatabaseColumn(List<Operation> operations) {
        return operations.stream().map(Operation::value).collect(Collectors.joining(","));
    }

    @Override
    public List<Operation> convertToEntityAttribute(String column) {
        return Arrays.stream(column.split(",")).map(Operation::from).toList();
    }
}
