package br.edu.insper.videoinsight.job.messaging;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import br.edu.insper.videoinsight.job.IntegrationTest;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.amqp.AmqpConnectException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageDeliveryMode;
import org.springframework.beans.factory.annotation.Autowired;

class OutboxPublisherTest extends IntegrationTest {
    @Autowired
    private OutboxPublisher publisher;

    @Test
    void publishesPendingEventsOnce() throws Exception {
        createJob();

        assertThat(publisher.publishPending()).isEqualTo(1);
        assertThat(publisher.publishPending()).isZero();

        var message = ArgumentCaptor.forClass(Message.class);
        verify(rabbitTemplate).send(eq("video-insight.processing"), eq("processing.requested"), message.capture());
        var properties = message.getValue().getMessageProperties();
        assertThat(properties.getContentType()).isEqualTo("application/json");
        assertThat(properties.getDeliveryMode()).isEqualTo(MessageDeliveryMode.PERSISTENT);
        var event = outbox.findAll().getFirst();
        assertThat(properties.getMessageId()).isEqualTo(event.getId().toString());
        assertThat(new String(message.getValue().getBody(), StandardCharsets.UTF_8)).isEqualTo(event.getPayload());
        assertThat(event.getPublishedAt()).isNotNull();
    }

    @Test
    void keepsEventsPendingWhenTheBrokerIsUnavailable() throws Exception {
        createJob();
        doThrow(new AmqpConnectException(new RuntimeException("down")))
                .when(rabbitTemplate).send(anyString(), anyString(), any(Message.class));

        assertThat(publisher.publishPending()).isZero();
        assertThat(outbox.findAll()).singleElement()
                .satisfies(event -> assertThat(event.getPublishedAt()).isNull());
    }

    @Test
    void schedulerDelegatesToPublisher() {
        var mockPublisher = mock(OutboxPublisher.class);

        new OutboxScheduler(mockPublisher).publishPending();

        verify(mockPublisher).publishPending();
    }
}
