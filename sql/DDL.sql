DROP TABLE CANCEL;
DROP TABLE RESERVE;
DROP TABLE CUSTOMER;
DROP TABLE SEATS;
DROP TABLE AIRPLANE;


CREATE TABLE AIRPLANE (
 airline VARCHAR(10) NOT NULL,
 flightNo VARCHAR(10),
 departureDateTime TIMESTAMP,
 arrivalDateTime TIMESTAMP NOT NULL, 
 departureAirport VARCHAR(20) NOT NULL,
 arrivalAirport VARCHAR(20) NOT NULL,
 CONSTRAINT pk_AIRPLANE PRIMARY KEY(flightNo, departureDateTime)
);


CREATE TABLE SEATS (
 flightNo VARCHAR(10),
 departureDateTime TIMESTAMP,
 seatClass VARCHAR(10), 
 price NUMBER NOT NULL,
 no_of_seats NUMBER NOT NULL,
 CONSTRAINT pk_seats PRIMARY KEY(flightNo, departureDateTime,seatClass),
 CONSTRAINT fk_seats FOREIGN KEY(flightNo, departureDateTime) 
  REFERENCES AIRPLANE(flightNo, departureDateTime)
);

CREATE TABLE CUSTOMER (
 cno VARCHAR(10),
 name VARCHAR(100) NOT NULL,
 passwd VARCHAR(100) NOT NULL,
 email VARCHAR(50) NOT NULL,
 passportNumber VARCHAR(9),
 CONSTRAINT pk_customer PRIMARY KEY(cno)
);

CREATE TABLE RESERVE (
 reserveId VARCHAR2(36) UNIQUE, -- CANCEL 테이블 중복추가 문제 해결 위해 추가함
 flightNo VARCHAR(10),
 departureDateTime TIMESTAMP,
 seatClass VARCHAR(10), 
 payment NUMBER NOT NULL,
 reserveDateTime TIMESTAMP NOT NULL,
 cno VARCHAR(10),
 CONSTRAINT pk_reserve PRIMARY KEY(flightNo, departureDateTime,seatClass, cno),
 CONSTRAINT fk_reserve1 FOREIGN KEY(flightNo, departureDateTime, seatClass) 
  REFERENCES SEATS(flightNo, departureDateTime, seatClass),
 CONSTRAINT fk_reserve2 FOREIGN KEY(cno) 
  REFERENCES CUSTOMER(cno)
);

CREATE TABLE CANCEL (
  reserveId VARCHAR2(36),
  flightNo VARCHAR(10),
  departureDateTime TIMESTAMP,
  seatClass VARCHAR(10), 
  refund NUMBER NOT NULL,
  cancelDateTime TIMESTAMP NOT NULL,
  cno VARCHAR(10),
  CONSTRAINT pk_cancel PRIMARY KEY (reserveId),
  CONSTRAINT fk_cancel1 FOREIGN KEY (flightNo, departureDateTime, seatClass) 
    REFERENCES SEATS(flightNo, departureDateTime, seatClass),
  CONSTRAINT fk_cancel2 FOREIGN KEY (cno) 
    REFERENCES CUSTOMER(cno)
);


-- 남은 좌석 수 stored procedure 구현 코드
CREATE OR REPLACE FUNCTION GET_REMAINING_SEATS(
    p_flightNo IN VARCHAR2,
    p_departureDateTime IN TIMESTAMP,
    p_seatClass IN VARCHAR2
) RETURN NUMBER IS
    total_seats NUMBER;
    reserved NUMBER;
    cancelled NUMBER;
BEGIN
    SELECT no_of_seats INTO total_seats
    FROM SEATS
    WHERE flightNo = p_flightNo 
      AND departureDateTime = p_departureDateTime 
      AND seatClass = p_seatClass;

    SELECT COUNT(*) INTO reserved
    FROM RESERVE
    WHERE flightNo = p_flightNo 
      AND departureDateTime = p_departureDateTime 
      AND seatClass = p_seatClass;

    RETURN total_seats - reserved;
END;
/
